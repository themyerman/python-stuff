
x = "When Johnny comes marching home hurrah hurrah"
print(x.upper)
print(x.lower)
print(x.startswith("When"))
print(x.replace("Johnny", "Tommy"))
print(len(x))
print(x[0])
print(x[12:])
print(x[5:9])
print(list(x))
print(":".join(list(x)))
print(x.split("comes"))
print(x.zfill(22))

print("There are %d letters in the alphabet" % 26)
letters = 26
print(f"There are {letters} letters in the alphabet")
planets = 8
pname = "mars"
print(f"There are {planets} planets. We are going to {pname}.")
