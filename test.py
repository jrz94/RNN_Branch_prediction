#!/usr/bin/python

import numpy as np
import tensorflow as tf
import argparse
import time
import os
import _pickle as cPickle
from utils import TextLoader
from word import WordLM
from itertools import groupby

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--test_file', type=str, default='data/trace/test.txt',
                        help="test file")
    parser.add_argument('--save_dir', type=str, default='model_test',
                        help='directory of the checkpointed models')
    args = parser.parse_args()
    test(args)


def run_epoch(session, m, data, data_loader, eval_op):
    costs = 0.0
    iters = 0
    state = tf.get_default_session().run(m.initial_lm_state)
    for step, (x, y) in enumerate(data_loader.data_iterator(data, m.batch_size, m.num_steps)):
        cost, state, _ = session.run([m.cost, m.final_state, eval_op],
                                     {m.input_data: x,
                                      m.targets: y,
                                      m.initial_lm_state: state})
        costs += cost
        iters += m.num_steps
    return np.exp(costs / iters)

##########################
def findlastword(test_file):
    data = list()
    with open(test_file, 'r') as f: 
        for line in f:
            line = line.strip()
            line = line.lower()
            data.append(line.split()[-1])
    return data

def process_testset(test_file):
    sentence_length = 0
    with open(test_file, 'r') as f: 
        for line in f:
            sentence_length = len(line.split()) + 1
    return sentence_length
    
def run_epoch2(session, m, data, data_loader, eval_op, test_file,sentence_length):
    iters = 0
    costs = 0.0
    acc = 0.0
    predict_index = list()
    state = tf.get_default_session().run(m.initial_lm_state)
    
    for step, (x, y) in enumerate(data_loader.data_iterator(data, m.batch_size, m.num_steps)):
        cost, probas, state, _ = session.run([m.cost, m.out_probs, m.final_state, eval_op],
                                     {m.input_data: x,
                                      m.targets: y,
                                      m.initial_lm_state: state})
        costs += cost
        iters += m.num_steps
        #print(np.argwhere(probas[0] == max(probas[0])))
        if (iters + 1)%sentence_length == 0:
            predict_index.append(np.argwhere(probas[0] == max(probas[0]))[0][0])     
    
    target_word = findlastword(test_file)
    target_index = data_loader.data_to_word_ids(target_word)
    
    for i in range(len(predict_index)):
        if predict_index[i] == target_index[i]:
            acc += 1
    #print("predict_index: {}".format(predict_index))
    #print("target_index: {}".format(target_index))
    # print("sentence_length: {}".format(sentence_length))
    # print("num of iters: {}".format(iters))
    return np.exp(costs / iters), (acc/ len(predict_index))
                

###########################


def test(test_args):
    start = time.time()
    with open(os.path.join(test_args.save_dir, 'config.pkl'), 'rb') as f:
        args = cPickle.load(f)
    data_loader = TextLoader(args, train=False)
    test_data = data_loader.read_dataset(test_args.test_file)
    
    args.word_vocab_size = data_loader.word_vocab_size
    args.out_vocab_size = data_loader.word_vocab_size
    print ("Word vocab size: " + str(data_loader.word_vocab_size) + "\n")

    # Model
    lm_model = WordLM

    print ("Begin testing...")
    # If using gpu:
    # gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=0.9)
    # gpu_config = tf.ConfigProto(log_device_placement=False, gpu_options=gpu_options)
    # add parameters to the tf session -> tf.Session(config=gpu_config)
    with tf.Graph().as_default(), tf.Session() as sess:
        initializer = tf.random_uniform_initializer(-args.init_scale, args.init_scale)
        with tf.variable_scope("model", reuse=None, initializer=initializer):
            mtest = lm_model(args, is_training=False, is_testing=True)

        # save only the last model
        saver = tf.train.Saver(tf.global_variables())
        tf.global_variables_initializer().run()
        ckpt = tf.train.get_checkpoint_state(args.save_dir)
        if ckpt and ckpt.model_checkpoint_path:
            saver.restore(sess, ckpt.model_checkpoint_path)

            
        sentence_length = process_testset(test_args.test_file)
        test_perplexity, acc = run_epoch2(sess, mtest, test_data, data_loader, tf.no_op(), test_args.test_file,sentence_length)
        print('Test accuracy is:{}'.format(acc))
        print("Test Perplexity: %.3f" % test_perplexity)
        print("Test time: %.0f" % (time.time() - start))
        '''
        #generate last word, to compute accuracy

        ################
        ############################
        #testdata without the last word
        data_loader2 = TextLoader(args, train=False)
        #sentence_length = process_testset(test_args.test_file)
        sentence_length = 10
        test_data2 = data_loader2.read_dataset('test_lack_1word.txt')
        #####################
        #compute the accuracy
        '''
                
        
        # sentence_length = process_testset(test_args.test_file)
        # test_perplexity, acc = run_epoch2(sess, mtest, test_data, data_loader, tf.no_op(), test_args.test_file,sentence_length)
        # print('accuracy is:{}'.format(acc))
        
if __name__ == '__main__':
    main()
