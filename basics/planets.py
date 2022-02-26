class CosmicException(Exception):
	pass


validPlanets = ["mercury","venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]


def helloPlanet(planetName):
	planetName = planetName.lower()
	if planetName not in validPlanets:
		raise CosmicException("Invalid Planet - {}".format(planetName))

	print("Hello {}".format(planetName))


#if __name__ == "__main__":
helloPlanet("Earth")
helloPlanet("Venus")
helloPlanet("Barzooom")