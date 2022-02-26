
dictionaryMap = {}
dictionaryMap["vowels"] = "aeiou"
dictionaryMap['consonants']="bcdfghjklmnpqrstvwxyz"

print(dictionaryMap.get("vowels"))


menu = {"coffee":10, "tea":5, "cookie":2, "chips": 5}
print(menu.get("coffee"))

print(menu.keys())
print(menu.values())


for k,v in menu.items():
		print(k,v)