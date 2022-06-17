from sklearn import svm
import numpy as np
import pandas as pd

##data preprocessing
def svm_():
    train_df = pd.read_csv('solution_data.csv')
    #train_df['pf'] = train_df['pf'].map({'p0': 1, 'f':0})
    train_df['target'] = train_df['target'].map({'p0':2, 'f2':1, 'f1':0})
    #train_df['target'] = train_df['target'].map({'p0':1, 'f2':0, 'f1':0})

    #print(train_df.iloc[:, [1]].values)
    
    # train_df.iloc[:, [1]] /=10
    # train_df.iloc[:, [2]] /=100
    # train_df.iloc[:, [3]] /=10
    # train_df.iloc[:, [4]] /=10
    # train_df.iloc[:, [5]] /=10
    # train_df.iloc[:, [6]] /= 1000
    # train_df.iloc[:, [7]] /= 100
    # train_df.iloc[:, [9]] /= 1000
    
    input = train_df.iloc[:,2:-1].values
    
    target = train_df.iloc[:, -1].values

    # for i in range(0, len(input)):
    #     print(input[i], target[i])

    s = svm.SVC(gamma=0.1, C=0.05, kernel='linear')
    s.fit(input, target)
    return s

if __name__ == '__main__':
    train_df = pd.read_csv('solution_data.csv')
    #train_df['pf'] = train_df['pf'].map({'p0': 1, 'f':0})
    train_df['target'] = train_df['target'].map({'p0':2, 'f2':1, 'f1':0})
    #train_df['target'] = train_df['target'].map({'p0':1, 'f2':0, 'f1':0})
    
    #print(train_df.iloc[:, [-1]].values)

    input = train_df.iloc[:,2:-1].values
    target = train_df.iloc[:, -1].values
    
    s = svm_()
    res = s.predict(input)
    print(res)

    print(input[3].reshape(1,-1))
    res_ = s.predict(input[3].reshape(1,-1))
    print(res_)

    conf = np.zeros((3,3))
    for i in range(len(res)):
        conf[res[i]][target[i]] +=1
    print(conf)

    no_correct= 0
    for i in range(3):
        no_correct += conf[i][i]
    accuracy = no_correct/len(res)
    print(accuracy*100)

