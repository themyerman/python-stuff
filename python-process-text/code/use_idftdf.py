"""Small TF-IDF example with sklearn."""

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception:
    print("Install scikit-learn to run this example.")
else:
    def build_tfidf(corpus):
        """Return feature names and tf-idf matrix for input corpus."""
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf = vectorizer.fit_transform(corpus)
        return vectorizer.get_feature_names_out(), tfidf


    def main():
        """Run TF-IDF demo."""
        vector_corpus = [
            "NBA is a basketball league",
            "Basketball is popular in America.",
            "TV in America telecast BasketBall.",
        ]
        features, tfidf = build_tfidf(vector_corpus)
        print("Tokens used as features are:")
        print(features)
        print("Size of array. Each row represents a document, each column represents a feature/token")
        print(tfidf.shape)
        print("Actual TF-IDF array:")
        print(tfidf.toarray())


    if __name__ == "__main__":
        main()