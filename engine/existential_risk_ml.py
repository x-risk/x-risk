# Run this script as a "standalone" script (terminology from the Django
# documentation) that uses the Djano ORM to get data from the database.
# This requires django.setup(), which requires the settings for this project.
# Appending the root directory to the system path also prevents errors when
# importing the models from the app.
if __name__ == '__main__':
    import sys
    import os
    import django
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__),
        os.path.pardir))
    sys.path.append(parent_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xrisk.settings")
    django.setup()

from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import connection, transaction
from engine.models import Assessment, Publication, MLModel, MLPrediction, Topic
from log import log

print("Loaded Django objects")

import datetime
import config
import numpy as np
import pandas as pd
import tensorflow as tf
import tflearn
from tensorflow.contrib import learn
from tflearn.layers.conv import conv_2d, max_pool_2d

print("Loaded ML libraries")

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

now = datetime.datetime.now()
day = now.day

# This script is run as a daily task (monthly is not possible), but we want it to be run only as a monthly task, on a specified day of the month (day = 14).
# if (day != 28):
#     exit()

print("This may take a while. Please wait!")

assessors = ['gorm', 'Sean_o_h', 'carhodes', 'lalitha', 'Haydn']
assessors = User.objects.filter(username__in=assessors)
print(assessors)

# Retrain the ML model until it is good enough, or up to five times (whichever is quicker).
i = 1
good_enough = False
while (good_enough != True and i <= 5):

    # Set the topic.
    search_topic = Topic.objects.get(topic='existential risk')

    # Get the publications.
    relevant_publications = Publication.objects.distinct().filter(
        assessment__in=Assessment.objects.filter(
            topic=search_topic,
            assessor__in=assessors,  # Change to all assessors when we have enough to get average assessments for publications.
            is_relevant=True
        )
    )
    assessed_publications = Publication.objects.distinct().filter(
        assessment__in=Assessment.objects.filter(
            topic=search_topic,
            assessor__in=assessors  # Change to all assessors when we have enough to get average assessments for publications.
        )
    )

    # Create a dataframe for publications that have been assessed (by humans).
    df = pd.DataFrame(list(assessed_publications.values('pk', 'title', 'abstract')))
    df['is_relevant'] = 0
    df['is_not_relevant'] = 1
    # Mark the relavant publications as relevant (1).
    for publication in relevant_publications:
        df.loc[df['pk'] == publication.pk, 'is_relevant'] = 1
        df.loc[df['pk'] == publication.pk, 'is_not_relevant'] = 0
    # Delete the publications without titles or abstracts.
    df = df[df['abstract'] != '']
    df = df[df['title'] != '']

    # Split the dataframe into a training set and a test set for machine learning.
    training_set = df.sample(frac=0.8)
    test_set = df.loc[~df.index.isin(training_set.index)]
    # Training set
    X_training = training_set['abstract']
    binomial_labels = []
    for y in training_set['is_relevant']:
        label = [y, 1 - y]
        binomial_labels.append(label)
    Y_training = binomial_labels
    Y_training = np.array(Y_training)
    binomial_labels = []
    # Test set
    X_test = test_set['abstract']
    for y in test_set['is_relevant']:
        label = [y, 1 - y]
        binomial_labels.append(label)
    Y_test = binomial_labels
    Y_test = np.array(Y_test)

    DATA = 'abstract'
    #DATA = 'title'
    data = list(training_set[DATA])

    # Set the number of features for the word encodings (number of features = number of words from the abstract or title to use for machine learning, which must be the same for all instances, and which will therefore be padded with zeros for instances with fewer words than this number).

    # The mean number of words could be used as the number of features.
    #MEAN_DOCUMENT_LENGTH = sum([len(datum.split(" ")) for datum in data]) / len(data)
    #N_FEATURES = int(round(MEAN_DOCUMENT_LENGTH, 0))

    # Or the maximum number of words could be used.
    #MAX_DOCUMENT_LENGTH = max([len(datum.split(" ")) for datum in data])
    #N_FEATURES = int(round(MEAN_DOCUMENT_LENGTH, 0))

    # Or another number could be used.
    N_FEATURES = 200

    # Create a vocabulary processor and replace each word with its index number in the vocabulary.
    vocab_processor = learn.preprocessing.VocabularyProcessor(N_FEATURES)
    X_training = np.array(list(vocab_processor.fit_transform(list(training_set[DATA]))))
    X_test = np.array(list(vocab_processor.fit_transform(list(test_set[DATA]))))

    # Cast the test and training data as the types expected by tensorflow.
    X_training = X_training.astype(np.int32)
    Y_training = Y_training.astype('float')
    X_test = X_test.astype(np.int32)
    Y_test = Y_test.astype('float')

    # Get a dictionary of index numbers for the words in the vocabulary.
    vocab_dict = vocab_processor.vocabulary_._mapping
    sorted_vocab = sorted(vocab_dict.items(), key = lambda X_training : X_training[1])
    vocabulary = list(list(zip(*sorted_vocab))[0])
    # Set the dimensions of the vocabulary for use in word embedding.
    INPUT_DIM = len(vocabulary)

    # Build the neural network.
    net = tflearn.input_data([None, N_FEATURES])
    # Word embedding
    net = tflearn.embedding(net, input_dim=INPUT_DIM, output_dim=16)
    net = tf.reshape(net, [-1, N_FEATURES, 16, 1])
    # Convolutions
    net = tflearn.layers.conv.conv_2d(net, nb_filter=2, filter_size=[2,3], strides=[1,1,1,1], activation='relu')
    # Uncomment the next line to add a max pool layer, which is commonly used after a convolution layer.
    #net = tflearn.layers.conv.max_pool_2d(net, kernel_size=2)
    # Dropout (to reduce overfitting)
    net = tflearn.layers.core.dropout(net, 0.5)
    net = tflearn.fully_connected(net, 2, activation='softmax')
    net = tflearn.regression(net, optimizer='adam', learning_rate=0.001,
                             loss='categorical_crossentropy')

    # Train the network.
    nn = tflearn.DNN(net, tensorboard_verbose=0)
    connection.connection.ping()  # Ping MySQL to maintain the connection.
    nn.fit(X_training, Y_training, validation_set=(X_test, Y_test), show_metric=True, batch_size=32)
    connection.connection.ping()  # Ping MySQL to maintain the connection.

    pred_test = nn.predict(X_test)
    results_df = pd.DataFrame(pred_test)
    results_df.columns = ['p_relevant', 'p_not_relevant']
    labels_df = pd.DataFrame(Y_test)

    # Set a threshold value for converting from model predictions (between 0 and 1)
    # to relevance categories (relevant or irrelevant). The threshold value
    # controls the tradeoff between recall (higher recall with lower threshold) and
    # precision (higher precision with higher threshold).

    # Find the threshold value by exploring a range of possible values.
    thresholds = np.arange(0.0, 0.33, 0.0001)
    tradeoffs = []

    # For each possible value, get the recall, precision, and accuracy scores.
    for threshold in thresholds:
        results_df['prediction'] = 0
        results_df['label'] = labels_df[0]
        results_df.loc[results_df['p_relevant'] > threshold, 'prediction'] = 1

        results_df['incorrect'] = abs(results_df['prediction'] - results_df['label'])
        incorrect = sum(results_df['incorrect'])
        accuracy = 1 - (incorrect / len(results_df))

        results_df['true_positive'] = 0
        results_df.loc[(results_df['prediction'] == 1) & (results_df['label'] == 1), 'true_positive'] = 1

        results_df['false_positive'] = 0
        results_df.loc[(results_df['prediction'] == 1) & (results_df['label'] == 0), 'false_positive'] = 1

        results_df['true_negative'] = 0
        results_df.loc[(results_df['prediction'] == 0) & (results_df['label'] == 0), 'true_negative'] = 1

        results_df['false_negative'] = 0
        results_df.loc[(results_df['prediction'] == 0) & (results_df['label'] == 1), 'false_negative'] = 1

        true_positives = sum(results_df['true_positive'])
        false_positives = sum(results_df['false_positive'])
        true_negatives = sum(results_df['true_negative'])
        false_negatives = sum(results_df['false_negative'])

        recall = true_positives / (true_positives + false_negatives)
        precision = true_positives / (true_positives + false_positives)

        tradeoffs.append([threshold, accuracy, precision, recall])

        print("Threshold:", threshold)
        connection.connection.ping() # Ping MySQL to maintain the connection.

    tradeoffs_df = pd.DataFrame(tradeoffs)
    tradeoffs_df.columns = ['threshold', 'accuracy', 'precision', 'recall']

    # Set the target recall values, then set threshold values that result in these recall values.
    target_recalls = [0.95, 0.75, 0.5]
    models_list = []
    models_dict = []
    for target_recall in target_recalls:
        results_df = tradeoffs_df[tradeoffs_df['recall'] >= target_recall]
        threshold = max(results_df['threshold'][results_df['recall'] >= target_recall])
        accuracy = float(results_df['accuracy'][results_df['threshold'] == threshold])
        precision = float(results_df['precision'][results_df['threshold'] == threshold])
        test_recall = float(results_df['recall'][results_df['threshold'] == threshold])
        models_list.append([threshold, accuracy, precision, test_recall, target_recall])
        models_dict.append({'threshold': threshold, 'accuracy': accuracy, 'precision': precision, 'test_recall': test_recall, 'target_recall': target_recall})
    models_df = pd.DataFrame(models_list)
    models_df.columns = ['threshold', 'accuracy', 'precision', 'test_recall', 'target_recall']
    print(models_df)

    if (min(models_df['precision']) >= 0.18):  # Define "good enough".
        good_enough = True
    else:
        i = i + 1
        print(i)
        print('We are retraining the model (because of low precision). This may take a while. Please wait!')
        connection.connection.ping()  # Ping MySQL to maintain the connection.
        tf.reset_default_graph()

# Save the machine-learning models to the database (MLModel), if the test recalls are greater than the target recalls. If not, then email the administrator.
ml_models = []
for model in models_dict:
    if (model.get('test_recall') < model.get('target_recall')):
        event = 'existential_risk_ml.py'
        note = 'Warning! When testing the performance of the newly trained machine-learning model for {topic}, the recall ({test_recall}) was lower than the target recall ({target_recall}). Therefore, the performance of this model was not saved in MLModel and its predictions were not saved in MLPrediction. If the target recall was 0.50, then you might need to set a value that is greater than 0.33 in thresholds = np.arange(0.0, 0.33, 0.0001).'.format(
                topic=search_topic,
                test_recall=model.get('test_recall'),
                target_recall=model.get('target_recall')
            )
        log(event=event, note=note)
        #TODO: Email the administrator.
        exit()
    ml_models.append(MLModel(
        topic=search_topic,
        threshold=model.get('threshold'),
        accuracy=model.get('accuracy'),
        precision=model.get('precision'),
        target_recall=model.get('target_recall'),
        test_recall=model.get('test_recall')
    ))

# Predict the relevance of publications that have not yet been assessed by humans.
unassessed_publications = Publication.objects.distinct().filter(
        search_topics=search_topic
    ).exclude(assessment__in=Assessment.objects.all()
)
df = pd.DataFrame(list(unassessed_publications.values('pk', 'title', 'abstract')))
df = df[df['abstract'] != '']
df = df[df['title'] != '']
df = df.reset_index()
X = np.array(list(vocab_processor.fit_transform(list(df['abstract']))))
X = X.astype(np.int32)
predictions = nn.predict(X)
predictions_df = pd.DataFrame(predictions)
predictions_df.columns = ['p_relevant', 'p_not_relevant']
predictions_df['pk'] = df['pk']
print(predictions_df.head())

# Save the predictions to the database (MLPrediction).
ml_predictions = []
for row in predictions_df.itertuples():
    ml_predictions.append(MLPrediction(
        publication=Publication.objects.get(pk=row.pk),
        topic=search_topic,
        prediction=row.p_relevant
    ))
with transaction.atomic():
    MLModel.objects.filter(topic=search_topic).delete()
    MLModel.objects.bulk_create(ml_models)
    MLPrediction.objects.filter(topic=search_topic).delete()
    MLPrediction.objects.bulk_create(ml_predictions)
    event = 'existential_risk_ml.py'
    note = 'A new machine-learning model was trained on the assessed publications for the topic, {topic}. Its performance on the test set was saved in MLModel and its predictions were saved in MLPrediction.'.format(topic=search_topic)
    log(event=event, note=note)
    EMAIL_HOST_USER = config.EMAIL_HOST_USER
    send_mail('New ML Model', note, EMAIL_HOST_USER, [EMAIL_HOST_USER])
