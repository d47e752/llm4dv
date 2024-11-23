import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

import math
import os
import matplotlib.ticker as mtick

bin_count = 196

def show_all_plots():
    legend_list = []
    fig = plt.figure(figsize=(15,7))
    ax = plt.subplot(111)

    for dirpath, dirnames, filenames in os.walk("."):
        print(dirpath)
        best_coverage = 0
        best_message_count = 1000
        current_best_df = None
        message_count_list = []
        for filename in filenames:
            if(".csv" in filename):
                df = pd.read_csv(dirpath + "\\" + filename,skiprows=1)
                message_count_list.append(df['Total Message#'].values[-1])
                if(df['Coverage Rate'].values[-1] > best_coverage or (df['Coverage Rate'].values[-1] == best_coverage and df['Total Message#'].values[-1] < best_message_count)):
                    current_best_df = df
                    best_coverage = df['Coverage Rate'].values[-1]
                    best_message_count = df['Total Message#'].values[-1]
        if(best_message_count != 1000):
            print("Best coverage: " + str(best_coverage))
            print("Message count for best: " + str(best_message_count))
            print("Avg msg/trial: " + str(np.mean(message_count_list)))
            print("Standard deviation: " + str(np.std(message_count_list)))
            ax.plot([0] + list(current_best_df['Total Message#']), [0] + list(current_best_df["Coverage Rate"]/bin_count*100), label=dirpath.split("\\")[-1])
            reset_df = current_best_df[current_best_df['Action'] == 'reset']
            ax.scatter(reset_df['Total Message#'], reset_df["Coverage Rate"]/bin_count*100, label=(dirpath.split("\\")[-1] + " reset"))

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True)
    ax.set_xlabel("Message Count")
    ax.set_ylabel("Coverage")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    plt.show()

def show_all_plots_no_few_shot():
    legend_list = []
    fig = plt.figure(figsize=(15,7))
    ax = plt.subplot(111)

    for dirpath, dirnames, filenames in os.walk("."):
        best_coverage = 0
        best_message_count = 1000
        current_best_df = None
        message_count_list = []
        if("few_shot" not in dirpath):
            print(dirpath)
            for filename in filenames:
                if(".csv" in filename):
                    df = pd.read_csv(dirpath + "\\" + filename,skiprows=1)
                    message_count_list.append(df['Total Message#'].values[-1])
                    if(df['Coverage Rate'].values[-1] > best_coverage or (df['Coverage Rate'].values[-1] == best_coverage and df['Total Message#'].values[-1] < best_message_count)):
                        current_best_df = df
                        best_coverage = df['Coverage Rate'].values[-1]
                        best_message_count = df['Total Message#'].values[-1]
            if(best_message_count != 1000):
                print("Best coverage: " + str(best_coverage))
                print("Avg msg/trial: " + str(np.mean(message_count_list)))
                print("Standard deviation: " + str(np.std(message_count_list)))
                ax.plot([0] + list(current_best_df['Total Message#']), [0] + list(current_best_df["Coverage Rate"]/bin_count*100), label=dirpath.split("\\")[-1])
                reset_df = current_best_df[current_best_df['Action'] == 'reset']
                ax.scatter(reset_df['Total Message#'], reset_df["Coverage Rate"]/bin_count*100, label=(dirpath.split("\\")[-1] + " reset"))

    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True)
    ax.set_xlabel("Message Count")
    ax.set_ylabel("Coverage")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    plt.show()

def few_shot_comparison():
    color_list=["b","g","r","c","m","y","k"]
    legend_list = []
    fig = plt.figure(figsize=(15,7))
    ax = plt.subplot(111)

    color_index = 0
    for dirpath, dirnames, filenames in os.walk("."):
        if("few_shot" in dirpath):
            linestyle="dotted"
        else:
            linestyle="solid"
        print(dirpath)
        best_coverage = 0
        best_message_count = 1000
        current_best_df = None
        message_count_list = []
        if("_2_II_a_iii" in dirpath and "memory_update" not in dirpath):
            for filename in filenames:
                if(".csv" in filename):
                    df = pd.read_csv(dirpath + "\\" + filename,skiprows=1)
                    message_count_list.append(df['Total Message#'].values[-1])
                    if(df['Coverage Rate'].values[-1] > best_coverage or (df['Coverage Rate'].values[-1] == best_coverage and df['Total Message#'].values[-1] < best_message_count)):
                        current_best_df = df
                        best_coverage = df['Coverage Rate'].values[-1]
                        best_message_count = df['Total Message#'].values[-1]
            if(best_message_count != 1000):
                print("Avg msg/trial: " + str(np.mean(message_count_list)))
                print("Standard deviation: " + str(np.std(message_count_list)))
                ax.plot([0] + list(current_best_df['Total Message#']), [0] + list(current_best_df["Coverage Rate"]/bin_count*100), label=dirpath.split("\\")[-1], linestyle=linestyle, color=color_list[math.floor(color_index/2)])
                reset_df = current_best_df[current_best_df['Action'] == 'reset']
                ax.scatter(reset_df['Total Message#'], reset_df["Coverage Rate"]/bin_count*100, label=(dirpath.split("\\")[-1] + " reset"), color=color_list[math.floor(color_index/2)])
                color_index += 1
    
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True)
    ax.set_xlabel("Message Count")
    ax.set_ylabel("Coverage")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    plt.show()

def memory_vs_incremental():
    color_list=["b","g","r","c","m","y","k"]
    legend_list = []
    fig = plt.figure(figsize=(15,7))
    ax = plt.subplot(111)

    color_index = 0
    for dirpath, dirnames, filenames in os.walk("."):
        if("incremental" in dirpath):
            linestyle="dotted"
        else:
            linestyle="solid"
        print(dirpath)
        best_coverage = 0
        best_message_count = 1000
        current_best_df = None
        message_count_list = []
        if("few_shot" not in dirpath):
            for filename in filenames:
                if(".csv" in filename):
                    df = pd.read_csv(dirpath + "\\" + filename,skiprows=1)
                    message_count_list.append(df['Total Message#'].values[-1])
                    if(df['Coverage Rate'].values[-1] > best_coverage or (df['Coverage Rate'].values[-1] == best_coverage and df['Total Message#'].values[-1] < best_message_count)):
                        current_best_df = df
                        best_coverage = df['Coverage Rate'].values[-1]
                        best_message_count = df['Total Message#'].values[-1]
            if(best_message_count != 1000):
                print("Avg msg/trial: " + str(np.mean(message_count_list)))
                print("Standard deviation: " + str(np.std(message_count_list)))
                ax.plot([0] + list(current_best_df['Total Message#']), [0] + list(current_best_df["Coverage Rate"]/bin_count*100), label=dirpath.split("\\")[-1], linestyle=linestyle)
                reset_df = current_best_df[current_best_df['Action'] == 'reset']
                ax.scatter(reset_df['Total Message#'], reset_df["Coverage Rate"]/bin_count*100, label=(dirpath.split("\\")[-1] + " reset"))
                color_index += 1
    
    box = ax.get_position()
    ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True)
    ax.set_xlabel("Message Count")
    ax.set_ylabel("Coverage")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    plt.show()

def main():
    few_shot_comparison()
if __name__ == "__main__":
    main()
