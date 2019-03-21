import csv
import os
from datetime import datetime
import bisect
import re


# How to use it:
#
# Example (1):
# Takes all the rows in <csvpath> which respects the regular expression '.*(/search)' in the 'REQUEST_URI' value
#   alldata = {}
#   alldata['ITEM'] = buildData(['.*(/search)'], ['REQUEST_URI'], csvpath)
#
# Example (2):
# Takes all the rows in <csvpath> which respects the regular expression '.*(\/corpus\/ra|\/corpus\/br)' in the 'HTTP_REFERER' value, AND
# respects the regular expression '.*(\/browse)' in the 'REQUEST_URI' value
#   alldata = {}
#   data_moves['ITEM'] = buildData(['.*(\/corpus\/ra|\/corpus\/br)','.*(\/browse)'], ['HTTP_REFERER','REQUEST_URI'], csvpath)

def scanLog(csvlogpath, txt_to_search, txt_field, printit = False):
    with open(csvlogpath) as csvfile:
        print('SCANNING ' + csvlogpath)
        reader = csv.DictReader(csvfile)
        count = 0
        data = []

        for row in reader:
            is_ok = True
            for i in range(len(txt_field)):

                pattern = re.compile(txt_to_search[i])
                if pattern.match(row[txt_field[i]]):
                    is_ok = True
                else:
                    is_ok = False
                    break

            if is_ok:
                count += 1

                my_val = {}
                for i in range(len(txt_field)):
                    my_val[txt_field[i]] = row[txt_field[i]]
                #data.append(my_val)
                data.append(row)

        return {'count': count, 'value': data}


def buildData(txt_list, txt_field_list, csvpath):
    data = {'x':[],'y':[],'value':[]}
    for filename in os.listdir(csvpath):
        if filename.endswith(".csv"):
            csvlogpath = csvpath+filename
            scanner = scanLog(csvlogpath,txt_list, txt_field_list)
            date = filename.replace("oc-", "").replace(".csv", "")

            date_val = datetime.strptime(date, '%Y-%m')
            bisect.insort(data['x'],date_val)
            ord_index = data['x'].index(date_val)
            data['y'].insert(ord_index,scanner['count'])
            data['value'].insert(ord_index,scanner['value'])
        else:
            continue

    return data

def observe(data,key, key_value = None):
    ##MY TEST SESSION PART-1
    myindex = {}

    def funindex(key,x):
        if key not in myindex:
            myindex[key] = {'value':[], 'count': 0}

        myindex[key]['value'].append(x)
        myindex[key]['count'] += 1

    for x in data:
        if key_value == None:
            funindex(x[key],x)
        else:
            funindex(x[key],x[key_value])

    return myindex

def sort_dict(var_dict, key, key_sort, reverse_opt = True):
    return sorted(var_dict.items() , reverse= reverse_opt, key=lambda x: x[key_sort])



def genCSV(path,data,g_label,x_label,y_label):
    #Generate the .CSV file
    FILE_TO_EDIT = path
    file_res = open(FILE_TO_EDIT,'w')
    file_res.write(g_label+','+x_label+','+y_label+'\n')
    file_res.close()


    file_res = open(FILE_TO_EDIT,'a')
    for key in data:
        for i in range(0,len(data[key]['x'])):
            file_res.write(key+','+data[key]['x'][i]+','+str(data[key]['y'][i])+'\n')
    file_res.close()
