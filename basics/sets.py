a = set([1,2,3])
b = set([2,3,5])
c = set([2,3])

intersect = a.intersection(b)
print("intersection of a and b is {}".format(intersect))

union = a.union(b)
print("union of a and b is {}".format(union))

difference = a.difference(b)
print("set difference between a and b is {}".format(difference))

difference = b.difference(a)
print("set difference between b and a is {}".format(difference))

subset = c.issubset(a)
print("is c subsect of a {}".format(subset))

subset = c.issubset(b)
print("is c subsect of b {}".format(subset))

subset = a.issubset(c)
print("is a subsect of c {}".format(subset))