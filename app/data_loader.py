import csv
with open('data/tickets.csv',"r",encoding='utf-8') as file:
    reader=csv.DictReader(file)
    for row in reader:
        print(row)