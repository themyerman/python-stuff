for i in range(1,10):
	print(i)


i=0
while i < 10:
	print(i)
	i += 1


i=0
while i < 10:
	i += 1
	print (i)
	if i == 5:
		break


i=0
while i < 10:
	i += 1
	if i % 2 == 0:
		continue;
	print(i)