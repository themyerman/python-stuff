try:
	import os
	import nltk

	#stopwords
	nltk.download('stopwords')
	from nltk.corpus import stopwords

	#stemming
	from nltk.stem import PorterStemmer 

	#lemma
	nltk.download('wordnet') 
	from nltk.stem import WordNetLemmatizer

except:
	print("install nltk and other tools!")

else:
	#read the file into a variable
	base_file = open(os.getcwd() + "/Spark-Course-Description.txt", "rt")
	raw_text = base_file.read()
	base_file.close()


	#extract tokens from variable
	token_list = nltk.word_tokenize(raw_text)
	print("First 20 tokens:", token_list[:20]) 
	print("Total tokens:", len(token_list))
	print("================================")

	#cleanse!
	token_list_cleansed = list(filter(lambda token: nltk.tokenize.punkt.PunktToken(token).is_non_punct, token_list))
	print("Token list after removing punctuation:", token_list_cleansed[:20])
	print("Total tokens after removing punctuation", len(token_list_cleansed))
	print("================================")

	#conver to lowercase
	token_list_lc = [word.lower() for word in token_list_cleansed]
	print("Token list after converting to lower case:", token_list_lc[:20])
	print("Total tokens after converting to lower case", len(token_list_lc))
	print("================================")


	#stopwords
	token_list_stop = list(filter(lambda token: token not in stopwords.words('english'), token_list_lc))
	print("Token list after removing stop words: ", token_list_stop[:20])
	print("Total tokens after removing stop words:", len(token_list_stop))
	print("================================")


	#stemming
	stemmer = PorterStemmer()
	token_list_stem = [stemmer.stem(word) for word in token_list_stop]
	print("Token list after stemming:", token_list_stem[:20])
	print("Total tokens after stemming:", len(token_list_stem))
	print("================================")


	#lemmatization
	lemmatizer = WordNetLemmatizer()
	token_list_lemma = [lemmatizer.lemmatize(word) for word in token_list_stop]
	print("Token list after lemma:", token_list_lemma[:20])
	print("Total tokens after lemma:", len(token_list_lemma))
	print("================================")

	#compare!
	print("Stop: ", token_list_stop[20], ", Stemmed: ", token_list_stem[20], ", Lemmatized:", token_list_lemma[20])
