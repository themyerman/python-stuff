try:
	import nltk
	import os
	nltk.download('punkt')
	nltk.download('stopwords')
	from nltk.corpus import stopwords
	nltk.download('wordnet')
	from nltk.stem import WordNetLemmatizer

	#for ngrams
	from nltk.util import ngrams
	from collections import Counter


except:
	print("download nltk and other packages!")

else:
	base_file = open(os.getcwd()+ "/Spark-Course-Description.txt", 'rt')
	raw_text = base_file.read()
	base_file.close()

	token_list = nltk.word_tokenize(raw_text)
	token_list2 = list(filter(lambda token: nltk.tokenize.punkt.PunktToken(token).is_non_punct, token_list))
	token_list3 = [word.lower() for word in token_list2]

	token_list4 = list(filter(lambda token: token not in stopwords.words('english'), token_list3))

	lemmatizer =WordNetLemmatizer()
	token_list5 = [lemmatizer.lemmatize(word) for word in token_list4]
	print("Total tokens :", len(token_list5))

	bigrams = ngrams(token_list5,2)
	trigrams = ngrams(token_list5,3)

	print("Most common bigrams:")
	print(Counter(bigrams).most_common(5))

	print("Most common trigrams:")
	print(Counter(trigrams).most_common(5))