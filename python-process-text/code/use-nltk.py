try:
	import os
	import nltk
	nltk.download('punkt')
	from nltk.corpus.reader.plaintext import PlaintextCorpusReader
except:
	print("Please download nltk and other tools")

else:

	#basic commands for reading from the corpus
	corpus = PlaintextCorpusReader(os.getcwd(), "Spark-Course-Description.txt")
	paragraphs = corpus.paras()
	sentences = corpus.sents()
	words = corpus.words()


	print(corpus.raw())
	print("================================")
	print ("Files in this corpus: ", corpus.fileids())
	print("Total paragraphs in this corpus:" , len(paragraphs))
	print("Total sentences in this corpus:", len(sentences))
	print("Total words in this corpus:", len(words))
	print("The first sentence:", sentences[0])
	print("Words in this corpus:", words)
	print("================================")

	#basic commands for analyzing the corpus
	corpus_freq_dist = nltk.FreqDist(words)
	most_common = corpus_freq_dist.most_common(10)

	print("Top 10 words in the corpus: ", most_common )
	print("Distribution for 'data':", corpus_freq_dist.get("data"))


