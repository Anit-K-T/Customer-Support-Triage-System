
import csv

def load_tickets():
    with open(
        "group1_tools_and_data/data/tickets.csv",
        "r",
        encoding="utf-8"
    ) as file:
        reader = csv.DictReader(file)
        tickets = list(reader)

    return tickets
