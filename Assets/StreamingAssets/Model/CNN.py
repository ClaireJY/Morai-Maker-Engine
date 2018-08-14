import tflearn, csv, random, glob, os
import tensorflow as tf
from tflearn import conv_2d, max_pool_2d, local_response_normalization, batch_normalization, fully_connected, regression, input_data, dropout, custom_layer, flatten, reshape, embedding
from tflearn.layers.recurrent import bidirectional_rnn, BasicLSTMCell
import numpy as np
from agent import *

class CNNAgent(Agent):

	def __init__(self):
		object.__init__("CNNAgent")


	def LoadModel(self):
		network = input_data(shape = [None, 16, 33, 14])
		network = conv_2d(network, 16, 2, activation='leaky_relu')
		network = max_pool_2d(network, 2)
		network = local_response_normalization(network)
		network = fully_connected(network, 224, activation='relu')
		network = tf.reshape(network, [-1, 16, 1, 14])
		network = regression(network, optimizer = 'adagrad', learning_rate = 0.00025, loss = 'categorical_crossentropy', name = 'target', batch_size=32)

		self.model = tflearn.DNN(network)
		self.model.load("./CNNmodel/model.tfl")


	# Convert sprite list to grid representation
	def ConvertToAgentRepresentation(self, objectsList, levelWidth, levelHeight):
		level = [['-' for _ in range(levelWidth)] for _ in range(levelHeight)]
		symbol_map = {'Ground':'X', 'Block':'S', 'Stair':'X', 'Pipe':'<', 'PipeBody':'[', 'Treetop':'X', 'Bridge':'X',
		              'Coin':'o', 'Question':'?', 'Cannon 1':'B', 'Cannon 2':'B', 'CannonBody':'b', 'Bar':'X', 'Bar 2':'X', 'Bar 3':'X',
					  'Goomba':'E', 'Koopa':'E', 'Koopa 2':'E', 'Hard Shell':'E', 'Hammer Bro':'E', 'Plant':'E', 'Winged Koopa':'E', 'Winged Koopa 2':'E'}

		# Add sprites to level representation
		for sprite in objectsList:
			if symbol_map.has_key(sprite.name):
				symbol = symbol_map[sprite.name]

				if symbol == '<':
					# - Construct entire pipe top
					level[sprite.y-16][sprite.x + 0] = '<'
					level[sprite.y-16][sprite.x + 1] = '>'
					level[sprite.y + 1-16][sprite.x + 0] = '['
					level[sprite.y + 1-16][sprite.x + 1] = ']'
				elif symbol == '[':
					# - Construct both pieces of pipe body
					level[sprite.y-16][sprite.x + 0] = '['
					level[sprite.y-16][sprite.x + 1] = ']'
				elif symbol == 'E':
					# - Limit enemies to one tile
					level[sprite.y-16][sprite.x] = 'E'
				elif symbol== 'X':
					level[sprite.y][sprite.x] = 'X'
					level[sprite.y+1][sprite.x] = 'X'
				else:
					# - Normal case
					for row in range(sprite.y, sprite.y + sprite.h):
						for column in range(sprite.x, sprite.x + sprite.w):
							level[row-16][column] = symbol

		return level


	# Clean up grid representation and convert to sprite list
	def ConvertToSpriteRepresentation(self, level):
		level_height = len(level)
		level_width = len(level[0])
		symbol_map = {'X':'Ground', 'Q':'Question', 'S':'Block', 'E':'Goomba', '?':'Question', '<':'Pipe', '[':'PipeBody', 'o':'Coin', 'B':'Cannon 1', 'b':'CannonBody'}
		size_map = {'Default':(1, 1), 'Pipe':(2, 2), 'PipeBody':(2, 1)}

		# Fill out pipes
		for level_y in range(0, level_height, -1):
			for level_x in range(level_width):
				symbol = level[level_y][level_x]
				if symbol == '[':
					if level_y > 0 and level_x < level_width - 1:
						level[level_y][level_x + 1] = ']'
					else:
						level[level_y][level_x] = '-'
				elif symbol == ']':
					if level_y > 0 and level_x > 0:
						level[level_y][level_x - 1] = '['
						# - Iterate upwards on the level while pipe elements are present
						offset_y = 0
						while level_y + offset_y > 0:
							if level[level_y + offset_y][level_x - 1] != '[' and level[level_y + offset_y][level_x] != ']':
								break
							elif level[level_y + offset_y][level_x - 1] == '<' or level[level_y + offset_y][level_x] == ']':
								break
							level[level_y + offset_y][level_x - 1] = '['
							level[level_y + offset_y][level_x + 0] = ']'
							offset_y += 1
						# - Add the top of the pipe
						level[level_y + offset_y][level_x - 1] = '<'
						level[level_y + offset_y][level_x + 0] = '>'
					else:
						level[level_y][level_x] = '-'
				elif symbol == '<':
					if level_y < level_height - 1 and level_x < level_width - 1:
						level[level_y + 0][level_x + 1] = '>'
						level[level_y + 1][level_x + 0] = '['
						level[level_y + 1][level_x + 1] = ']'
					else:
						level[level_y][level_x] = '-'
				elif symbol == '>':
					if level_y < level_height - 1 and level_x > 0:
						level[level_y + 0][level_x - 1] = '<'
						level[level_y + 1][level_x - 1] = '['
						level[level_y + 1][level_x + 0] = ']'
					else:
						level[level_y][level_x] = '-'

		# Convert map to sprite list
		additions = []
		for level_y in range(level_height):
			for level_x in range(level_width):
				symbol = level[level_y][level_x]
				if symbol_map.has_key(symbol):
					name = symbol_map[symbol]
					size_x, size_y = size_map[name] if size_map.has_key(name) else size_map['Default']
					additions.append(Sprite(name, level_x, 16-level_y, size_x, size_y))

		return additions


	# Run the model to generate new suggestions on the grid representation
	def RunModel(self, level):
		window_height = 16
		window_width = 33
		level_height = len(level) - window_height +1
		level_width = len(level[0]) - window_width +1
		symbols = ['!', '-', 'X', '*', 'Q', 'S', 'E', '?', '<', '[', ']', '>', 'o', 'B', 'b']

		# Extract obfuscated windows from level
		windows = np.zeros([level_height * level_width, window_height, window_width, len(symbols)])
		for level_y in range(level_height):
			for level_x in range(level_width):
				for window_y in range(window_height):
					for window_x in range(window_width):
						symbol = '!' if window_x == (window_width / 2) else level[level_y + window_y][level_x + window_x]
						windows[level_y * level_width + level_x][window_y][window_x][symbols.index(symbol)] = 1

		# Run the model
		results = self.model.predict(windows)

		# Update level representation with model results
		for level_y in range(level_height):
			for level_x in range(level_width):
				for window_y in range(window_height):
					# - Probabilitic sampling from model results
					one_hot = results[level_y * level_width + level_x][window_y][0]
					one_hot = np.divide(one_hot, sum(one_hot))
					level[level_y + window_y][level_x + window_width / 2] = np.random.choice(symbols, p=one_hot)
					#maxOneHot = np.max(one_hot)
					#indx = list(one_hot).index(maxOneHot)
					#level[level_y + window_y][level_x + window_width / 2] = symbols[indx]

		return level