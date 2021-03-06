####### TRAINING CIFAR-10 CONVNET ##############
# @author Melanie Ducoffe #
# @date 10/02/2016 #
####################
from load_data import load_datasets
from training_svhn import build_training, training_committee
import numpy as np
import theano
import theano.tensor as T
from active_function import active_selection
from contextlib import closing
import os


def record_state(n_train_batches, n_train, best_train, best_valid, best_test, repo=None, filename=None):
	ratio = "RATIO :"+str(1.*n_train_batches/n_train*100)
	train = "TRAIN : "+str(best_train*100)
	valid = "VALID : "+str(best_valid*100)
	test = "TEST : "+str(best_test*100)
	if filename is None:
		print ratio
		print train
		print valid
		print test
	else:
		with closing(open(os.path.join(repo, filename), 'a')) as f:
			f.write(ratio+"\n"+train+"\n"+valid+"\n"+test+"\n")

"""
3 options possible :
- 'rand' for random selection
- 'uncertainty_s' for uncertain sampling
- 'qbc' for query by committee
"""
 
def training(repo, learning_rate, batch_size, filenames, option="qbc", record_repo=None, record_filename=None):

	print 'LOAD DATA'
	(x_train, y_train), (x_valid, y_valid), (x_test, y_test) = load_datasets(repo, filenames)

	print 'BUILD MODEL'
	train_f, valid_f, test_f, model, reinit = build_training(lr=learning_rate)

	n_train = len(y_train)/batch_size
	n_valid = len(y_valid)/batch_size
	n_test = len(y_test)/batch_size

	epochs = 2000
	best_valid = np.inf; best_train = np.inf; best_test=np.inf
	init_increment = 5 # 20 5 8 
	increment = 0
	n_train_batches=int (n_train*1./100.)
	state_of_train = {}
	state_of_train['TRAIN']=best_train; state_of_train['VALID']=best_valid; state_of_train['TEST']=best_test; 
	print 'TRAINING IN PROGRESS'
	for epoch in range(epochs):

		try:
			for minibatch_index in range(n_train_batches):
				x_value = x_train[minibatch_index*batch_size:(minibatch_index+1)*batch_size]
				y_value = y_train[minibatch_index*batch_size:(minibatch_index+1)*batch_size].reshape((batch_size, 1))
				value = train_f(x_value, y_value)
				if np.isnan(value):
					import pdb
					pdb.set_trace()
			valid_cost=[]
			for minibatch_index in range(n_valid):
				x_value = x_valid[minibatch_index*batch_size:(minibatch_index+1)*batch_size].reshape((batch_size, 3, 32, 32))
				y_value = y_valid[minibatch_index*batch_size:(minibatch_index+1)*batch_size].reshape((batch_size, 1))
				value = test_f(x_value, y_value)
				valid_cost.append(value)

			# deciding when to stop the training on the sub batch
	    		valid_result = np.mean(valid_cost)
	    		if valid_result <= best_valid*0.95:
				model.save_model() # record the best architecture so to apply active learning on it (overfitting may appear in a few epochs)
	    			best_valid = valid_result
				# compute best_train and best_test
				train_cost=[]
				for minibatch_train in range(n_train_batches):
					x_value = x_train[minibatch_train*batch_size:(minibatch_train+1)*batch_size].reshape((batch_size, 3, 32, 32))
					y_value = y_train[minibatch_train*batch_size:(minibatch_train+1)*batch_size].reshape((batch_size, 1))
					train_cost.append(valid_f(x_value, y_value))
				test_cost=[]
				for minibatch_test in range(n_test):
					x_value = x_test[minibatch_test*batch_size:(minibatch_test+1)*batch_size].reshape((batch_size, 3, 32, 32))
					y_value = y_test[minibatch_test*batch_size:(minibatch_test+1)*batch_size].reshape((batch_size, 1))
					test_cost.append(test_f(x_value, y_value))
				best_train=np.mean(train_cost)
				best_test=np.mean(test_cost)
	    			increment=init_increment
			else:
				increment-=1

			if increment==0:
				# keep the best set of params found during training
				model.load_model()
				increment = init_increment
				record_state(n_train_batches, n_train, best_train, best_valid, best_test, record_repo, record_filename)
				# record in a file
				if state_of_train['VALID'] > best_valid :
					state_of_train['TRAIN']=best_train
					state_of_train['VALID']=best_valid
					state_of_train['TEST']=best_test;
				(x_train, y_train), n_train_batches = active_selection(model, x_train, y_train, n_train_batches, batch_size, valid_f, option)
				model.initialize()
				reinit()
				best_valid=np.inf; best_train=np.inf; best_test=np.inf

		except KeyboardInterrupt:
			# ask confirmation if you want to check state of training or really quit
			print 'BEST STATE OF TRAINING ACHIEVED'
			print "RATIO :"+str(1.*n_train_batches/n_train*100)
			print "TRAIN : "+str(state_of_train['TRAIN']*100)
			print "VALID : "+str(state_of_train['VALID']*100)
			print "TEST : "+str(state_of_train['TEST']*100)
			import pdb
			pdb.set_trace()
		

if __name__=="__main__":
	# read options
	import sys
	opt="qbc"; record_repo=None; record_filename=None
	if len(sys.argv)>=2:
		opt=sys.argv[1]
		if not( opt in ['qbc', 'uncertainty', 'random']):
			raise Exception('unknown option for the active decision module %s', opt)
		if len(sys.argv)>=4:
			record_repo=sys.argv[2];
			record_filename=sys.argv[3]
	repo="/home/ducoffe/Documents/Code/datasets/svhn"
	filenames={}; 
	filenames["x_train"]="svhn_pickle_v3_x_train";
	filenames["y_train"]="svhn_pickle_v3_y_train";
	filenames["y_test"]="svhn_pickle_v3_y_test";
	filenames["x_test"]="svhn_pickle_v3_x_test";
	learning_rate = 1e-4
	batch_size = 32
	training(repo, learning_rate, batch_size,filenames, opt, record_repo, record_filename)
