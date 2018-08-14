#!/usr/bin/env python

import socket, csv, time
from agent import *
from gragent import *
#from CNN import *
from mkagent import *

TCP_IP = '127.0.0.1'
TCP_PORT = 5017
BUFFER_SIZE = 1024

print ("Before load agent")
#TODO; pick between options
currAgent = MKAgent()
#currAgent = GRAgent()
currAgent.LoadModel()
print ("Agent loaded")



s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind((TCP_IP, TCP_PORT))
s.listen(1)

conn, addr = s.accept()
#print 'Connection address:', addr
while 1:
    data = conn.recv(BUFFER_SIZE)
    if data:
        print ("Data received")
        #Grab from data file
        source = open(data, "rb")
        reader = csv.reader(source)
        readRow = False
        levelSize = []
        levelSprites = []
        for row in reader:
            print (row)
            if readRow:
                levelSprites.append(Sprite(row[0], int(row[1]), int(row[2]), int(row[3]), int(row[4])))
            else:
                levelSize = [int(row[0]), int(row[1])]
                readRow = True
        cloneList = list(levelSprites)#in case the agent mucks with the list
        agentLevel = currAgent.ConvertToAgentRepresentation(levelSprites, levelSize[0], levelSize[1])
        updatedLevel =currAgent.RunModel(agentLevel)
        spriteList = currAgent.ConvertToSpriteRepresentation(updatedLevel)
        levelSprites = cloneList
        finalSpriteList = []
        print ("Size of spriteList: "+str(len(spriteList)))
        for s in spriteList:
            print ([s.name,s.x,s.y])
            addIt = True
            for l in levelSprites:
                if l.x==s.x and s.y==l.y:
                    addIt = False
                    break
            if addIt:
                finalSpriteList.append(s)
        print()

        #Sort
        finalSpriteList = sorted(finalSpriteList, key=lambda x: (x.x,x.y))
        print (len(finalSpriteList))
        # Write additions to file
        printedList = []
        with open('./additions.csv', 'wb') as additions_file:
            writer = csv.writer(additions_file)
            for f in finalSpriteList:
                row = [f.name,f.x,f.y]
                if not row in printedList:
                    writer.writerow(row)
                    printedList.append(row)
        time.sleep(2) 
        conn.close()
        time.sleep(2) 
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((TCP_IP, TCP_PORT))
        s.listen(1)
        conn, addr = s.accept()
