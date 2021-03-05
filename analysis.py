from typing import Optional, List, Tuple
from nltk.corpus import sentiwordnet as swn
import nltk
from nltk.stem import WordNetLemmatizer
from nltk.corpus import wordnet as wn

POS = 0
NEG = 1
OBJ = 2
UNKN = 3

LEMMATIZER = WordNetLemmatizer()


class TextAnalysis:

    def __init__(self, text: str):
        self._txt: str = text
        self._sentiment: Optional[Tuple[int, int, int, int]] = None
        self._avg_sentiment: Optional[Tuple[float, float, float, float]] = None
        self._sent_tokens: Optional[List[List[str]]] = None
        self._sents: Optional[List[str]] = None
        self._num_tokens: Optional[int] = None

    def __repr__(self):
        return f"<TextAnalysis \"{self._txt}\">"

    def __str__(self):
        return f"Analysis of \"{self._txt}\"\nNumber of sentences: {len(self.get_sents())}\n" \
               f"Number of tokens: {self.get_num_tokens()}\n" \
               f"Total positivity score: {self.get_sentiment()[POS]}\n" \
               f"Total negativity score: {self.get_sentiment()[NEG]}\n" \
               f"Total objectivity score: {self.get_sentiment()[OBJ]}\n" \
               f"Avg positivity score: {self.get_avg_sentiment()[POS]}\n" \
               f"Avg negativity score: {self.get_avg_sentiment()[NEG]}\n" \
               f"Avg objectivity score: {self.get_avg_sentiment()[OBJ]}"

    def get_tokens(self):
        if self._sent_tokens is None:
            tokens = []
            for sent in self.get_sents():
                tokens.append(nltk.word_tokenize(sent))
            self._sent_tokens = tokens

        return self._sent_tokens

    def get_sents(self):
        if self._sents is None:
            self._sents = nltk.sent_tokenize(self._txt)

        return self._sents

    def get_pos(self):
        if self._sent_tokens is None:
            pos = []
            for sent in self.get_tokens():
                pos.append(nltk.pos_tag(sent))
            self._pos = pos

        return self._pos

    def get_num_tokens(self):
        if self._num_tokens is None:
            num_tokens = 0
            for sent in self.get_tokens():
                num_tokens += len(sent)
            self._num_tokens = num_tokens

        return self._num_tokens

    def get_sentiment(self):
        if self._sentiment is None:
            total_positive = 0
            total_negative = 0
            total_objective = 0
            total_unknown = 0

            for sent in self.get_tokens():
                for token in sent:

                    senti_concepts = list(swn.senti_synsets(LEMMATIZER.lemmatize(token)))
                    if len(senti_concepts) > 0:
                        senti_concept = senti_concepts[0]

                        total_positive += senti_concept.pos_score()
                        total_negative += senti_concept.neg_score()
                        total_objective += senti_concept.obj_score()
                    else:
                        total_unknown += 1

            self._sentiment = total_positive, total_negative, total_objective, total_unknown

        return self._sentiment

    def get_avg_sentiment(self):
        if self._avg_sentiment is None:
            sentiment = self.get_sentiment()
            num_tokens = self.get_num_tokens()
            self._avg_sentiment = (sentiment[POS] / num_tokens,
                                   sentiment[NEG] / num_tokens,
                                   sentiment[OBJ] / num_tokens,
                                   sentiment[UNKN] / num_tokens)

        return self._avg_sentiment


if __name__ == "__main__":
    t_analysis = TextAnalysis("happy joyful love good")
    print(t_analysis.get_sentiment())
    print(t_analysis.get_avg_sentiment())
