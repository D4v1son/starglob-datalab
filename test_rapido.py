# test_rapido.py (borrar después)
from starglob_datalab.configuration import load_config
from starglob_datalab.generation.tickets import generate_tickets

config = load_config("config/tickets_demo.yaml")
df = generate_tickets(config)

print(df.shape)
print(df.head())
print(df["status"].value_counts())