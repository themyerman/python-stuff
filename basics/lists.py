def getSquare(max=20):
	newList = []
	for x in range(max):
		newList.append(x*x)

	return newList


print(getSquare(50))


newList = [x * x for x in range(50)]
print(newList)