try:
	from sklearn.feature_extraction.text import TfidfVectorizer
	import pandas as pd

except:
	print("install sklearn and pandas")

else:

	#create small corpus
	vector_corpus = [
		"NBA is a basketball league",
		"Basketball is popular in America.",
		"TV in America telecast BasketBall."
	]

	#create a vectorizer for the english language
	vectorizer = TfidfVectorizer(stop_words="english")

	#create the vector
	tfidf = vectorizer.fit_transform(vector_corpus)

	print("Tokens used as features are:")
	print(vectorizer.get_feature_names())

	print("Size of array. Each row represents a document, each column represents a feature/token")
	print(tfidf.shape)

	print("Actual TF-IDF array:")
	print(tfidf.toarray())