import solana

def list_module(module, module_name):
    print(f"\n{module_name} module contents:")
    for attr in dir(module):
        if not attr.startswith('_'):
            print(attr)

list_module(solana, "solana")

try:
    from solana.rpc.api import Client
    print("\nsolana.rpc.api module imported successfully")
except ImportError:
    print("solana.rpc.api module not found")

try:
    from solana.transaction import Transaction
    print("solana.transaction.Transaction imported successfully")
except ImportError:
    print("solana.transaction.Transaction not found")

try:
    from solana.publickey import PublicKey
    print("solana.publickey.PublicKey imported successfully")
except ImportError:
    print("solana.publickey.PublicKey not found")

try:
    from solana.keypair import Keypair
    print("solana.keypair.Keypair imported successfully")
except ImportError:
    print("solana.keypair.Keypair not found")

try:
    from solana.system_program import transfer, TransferParams
    print("solana.system_program imported successfully")
except ImportError:
    print("solana.system_program not found")