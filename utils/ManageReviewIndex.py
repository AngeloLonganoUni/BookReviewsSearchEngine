from ast import Dict
import os
from typing import Callable

import whoosh.index as index
from whoosh import scoring
from whoosh.qparser import QueryParser

from utils.abstract.ManageIndexAbstract import ManageIndexAbstract
from utils.models.DocumentModel import DocumentModel
from utils.models.Scheme import ReviewScheme
from utils.services.path_used_service import INDEX_DIR_PATH


class MangeReviewIndex(ManageIndexAbstract):
    """
    Classe che gestisce tutte le funzionalità dell'index
    """
    schema = ReviewScheme()

    def __init__(self):
        """
        Costruttore della classe
        inizializza le variabili di istanza
        """
        self.index_directory_path = INDEX_DIR_PATH
        self.ix = None
        self.default_field = "text"

        index_directory = os.listdir(self.index_directory_path)
        if len(index_directory) == 0:
            self.ix = index.create_in(self.index_directory_path, MangeReviewIndex.schema)
        else:
            self.ix = index.open_dir(self.index_directory_path)

    def search_index(self, query: str, field: str, sentiment: str, max_results: int, reversed_sort: int, sort_by: str):
        """
        La funzione si occupa di fare una ricerca all'interno del nostro index utilizzando i parametri forniti

        :param query:
        :param field:
        :param sentiment:
        :param max_results:
        :param reversed_sort:
        :param sort_by:
        :return:
        """
        query_parser = QueryParser(self.default_field, schema=MangeReviewIndex.schema)
        query_parsed = query_parser.parse(query)
        results = []
        with self.ix.searcher(weighting=scoring.BM25F()) as searcher:
            query_results = searcher.search(query_parsed, sortedby=sort_by, reverse=reversed_sort,
                                            limit=max_results * 2)
            query_results_scored = query_results.scored_length()
            print("ricerca...")
            print("----------RESULTS-----------")
            print("Scored results: ", query_results_scored)
            print("Total estimated results between: ", query_results.estimated_min_length(), "and",
                  query_results.estimated_length())

            for result in query_results:
                if len(results) >= max_results:
                    break
                if sentiment != "None":
                    result_sentiments = {"negative_sentiment": result["negative_sentiment"],
                                         "neutral_sentiment": result["neutral_sentiment"],
                                         "positive_sentiment": result["positive_sentiment"]}
                    sorted_sentiments = sorted(result_sentiments.items(), key=lambda x: x[1], reverse=True)

                if sentiment == "None" or sorted_sentiments[0][0] == sentiment:
                    document = {}
                    for i in result:
                        document[i] = result[i]
                        if i == "text":
                            print(i + ": ", result[i][:300] + "...")
                        else:
                            print(i + ": ", result[i])
                    document["highlights"] = result.highlights(field)
                    results.append(document)

                print(result[field], "\n")
                print(result.highlights(field))

                print("\n")
                print("\n")

        return results

    def writer_function(self) -> Dict:
        """
        Restituisce le due funzioni per aggiungere un documento e per chiudere l'index scrivendo le modifiche
        :return: {"add_document", "save_document"}
        """
        writer = self.ix.writer()
        return {"add_document": writer.add_document, "save_document": writer.commit}

    def suggest_words(self, mistyped_word: str):
        """
        Restituisce delle possibili correzioni al termine in mistyped_word usando il corpus dell'index
        :param mistyped_word:
        """
        with self.ix.searcher() as s:
            corrector = s.corrector("text")
            print(corrector.suggest(mistyped_word, limit=3))

    def correct_query(self, query):
        """
        Restituisce una correzione della query presente in query

        :param query:
        :return:
        """
        query_parser = QueryParser(self.default_field, schema=MangeReviewIndex.schema)
        query_parsed = query_parser.parse(query)

        with self.ix.searcher() as s:
            corrected = s.correct_query(query_parsed, query)
            if corrected.query != query_parsed:
                print("Did you mean:", corrected.string + "?")
                return corrected.string
