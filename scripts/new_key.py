"""Generate a fresh Injective-compatible keypair.

Prints the hex private key, the bech32 inj1... address, and the ethereum 0x... address.
Save the private key to .env. Save the mnemonic somewhere safe if you want to recover
the wallet later — the private key alone is enough to use the wallet.

Usage: uv run python scripts/new_key.py
"""

from __future__ import annotations

from pyinjective.wallet import PrivateKey


def main() -> None:
    mnemonic, priv = PrivateKey.generate()
    pub = priv.to_public_key()
    addr = pub.to_address()

    print("New Injective keypair:")
    print()
    print(f"  PRIVATE KEY (hex):  {priv.to_hex()}")
    print(f"  Address (bech32):   {addr.to_acc_bech32()}")
    print(f"  Address (eth 0x):   {addr.get_ethereum_address()}")
    print()
    print(f"  Recovery mnemonic:  {mnemonic}")
    print()
    print("Next steps:")
    print("  1. Fund testnet:  https://testnet.injective.network/")
    print("  2. Put the private key in .env as INJECTIVE_PRIVATE_KEY=...")
    print("  3. Save the mnemonic somewhere safe (offline). Do NOT commit it.")


if __name__ == "__main__":
    main()
