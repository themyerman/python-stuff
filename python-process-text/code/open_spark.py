import os

with open(os.getcwd() + "/Spark-Course-Description.txt", 'r') as fh:
	filedata = fh.read()

print("Data read from file :", filedata[0:200])