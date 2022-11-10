from common_module import *
import tomotopy as tp

# Loading NLTK Modules
import nltk
# nltk.download('all')
nltk.download('stopwords')
from nltk.corpus import stopwords

class topicModel:
    
  def __init__(self, data_path):
    self.topic_models = {}
    self.model_path = os.path.join(data_path,"models/topicmodels/") 
    for i in os.listdir(self.model_path):
        self.topic_models[int(i.split(".")[0].split("_")[-1])] = tp.MGLDAModel.load(os.path.join(self.model_path, i))          
    
  # perform pre-processing steps using lemmatization, stop-words and unnecessary punctuation removal
  def preprocess_article_text(self, doc_article):
    """
    Accept pandas series, then:
    1. Apply Word stemming
    2. Apply Stop Word removal
    """
    # clean
    doc_article = doc_article.lower()
    # remove stop words
    words = nltk.word_tokenize(doc_article)
    stop_words = stopwords.words('english')
    stop_words = stop_words + ["said", "says", "just", "like", "would", "could", "use", "told", "new", "also", "thats", "even","dont"]
    words = [word for word in words if word not in stop_words and len(word) > 3]
    doc_article = ' '.join(words)
    doc_article = doc_article.replace('\xa0', '')
    doc_article = re.sub('[!"#$%&\'()’*+,-./:;<=>?—@[\\]^_`{|}~’]', '', doc_article)
    # remove digits 
    doc_article = re.sub("^\d+\s|\s\d+\s|\s\d+$", " ", doc_article)

    return doc_article

  def multi_grainLdaModel_train(self, doc_list):
    # k_g is th number of global topics, while k_l is the number of local topics
    mdl = tp.MGLDAModel(k_g=10, k_l=10, min_cf=20, min_df=30)
    for document in doc_list:
        mdl.add_doc(document.split())

    iterations = 10
    for i in range(0, 100, iterations):
            mdl.train(iterations)
            print('Iteration: {}\tLog-likelihood: {}'.format(i, mdl.ll_per_word))
    result_dict_train = self.extract_topic(mdl)
    return result_dict_train, mdl

  def extract_topic(self, mdl):
    result_dict = {}
    topic_dict = {}
    extractor = tp.label.PMIExtractor(min_cf=20, min_df=30, max_len=5, max_cand=10000)
    cands = extractor.extract(mdl)

    # ranking the candidates of labels for a specific topic
    labeler = tp.label.FoRelevance(mdl, cands, min_df=30, smoothing=1e-2, mu=0.25)

    # for k in range(mdl.k):
    #   print("== Topic #{} ==".format(k))
    #   print("Labels:", ', '.join(label for label, score in labeler.get_topic_labels(k, top_n=5)))
    #   for word, prob in mdl.get_topic_words(k, top_n=10):
    #     print(word, prob, sep='\t')

    max_topic_num = 0
    for k in range(mdl.k_g):
        cur_topic = "topic#"+str(k)
        result_dict[cur_topic] = {}
        result_dict[cur_topic]["labels"] = (', '.join(label for label, score in labeler.get_topic_labels(k, top_n=5)))
        # result_dict[cur_topic]['topics'] = mdl.get_topic_words(k, top_n=10)
        result_dict[cur_topic]['topics'] = ' ,'.join([i[0] for i in mdl.get_topic_words(k, top_n=10)])
        max_topic_num +=1

    for k in range(mdl.k_l):
      cur_topic = "topic#"+str(max_topic_num+k)
      result_dict[cur_topic] = {}
      result_dict[cur_topic]["labels"] = (', '.join(label for label, score in labeler.get_topic_labels(mdl.k_g + k, top_n=5)))
      # result_dict[cur_topic]['topics'] = mdl.get_topic_words(mdl.k_g + k, top_n=10)
      result_dict[cur_topic]['topics'] = ' ,'.join([i[0] for i in mdl.get_topic_words(mdl.k_g + k, top_n=10)])
     
    return result_dict

  def multi_grainLdaModel_predict(self, doc_list, mdl):
    pred_result = {}
    docs_words = []
    for doc in doc_list:
      docs_words = docs_words + doc.strip().split()
    doc_inst = mdl.make_doc(docs_words)
    topic_dist, ll = mdl.infer(doc_inst)
    # sort the topic dist and take index
    topic_dist_arr = np.array(topic_dist)
    topic_dist_idx = topic_dist_arr.argsort()[::-1]
    mdl_topic = self.extract_topic(mdl)
    idx = 0
    for i in topic_dist_idx:
      if topic_dist[i]>0:
        pred_result["topic#"+str(idx)] = mdl_topic["topic#"+str(i)]
      idx+=1
    return pred_result

  def do_pridict(self, article, clas_label):
    mdl = self.topic_models[int(clas_label)]
    topic_result = self.multi_grainLdaModel_predict(article.tolist(), mdl)
    return topic_result
      
