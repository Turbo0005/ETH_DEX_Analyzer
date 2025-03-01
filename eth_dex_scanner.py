import requests
import time
from datetime import datetime

class TokenTransactions:
    def __init__(self):
        # 在此处填写自己的 Etherscan API Key
        # 获取 API Key: https://etherscan.io/apis
        self.etherscan_api_key = "YOUR_ETHERSCAN_API_KEY"
        
        self.etherscan_base_url = "https://api.etherscan.io/api"
        self.dexscreener_base_url = "https://api.dexscreener.com/latest/dex"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def get_pair_address(self, token_address):
        """通过Uniswap V2 Factory合约获取pair地址"""
        # Uniswap V2 Factory合约地址
        factory_address = "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f"
        # WETH地址
        weth_address = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
        
        # getPair(token0, token1)的函数签名
        function_signature = "0xe6a43905"
        
        # 对参数进行padding
        token0 = min(token_address.lower(), weth_address.lower())
        token1 = max(token_address.lower(), weth_address.lower())
        data = function_signature + token0[2:].zfill(64) + token1[2:].zfill(64)
        
        params = {
            'module': 'proxy',
            'action': 'eth_call',
            'to': factory_address,
            'data': data,
            'tag': 'latest',
            'apikey': self.etherscan_api_key
        }
        
        try:
            response = requests.get(self.etherscan_base_url, params=params)
            response.raise_for_status()
            result = response.json()
            if result['result']:
                # 解析返回的pair地址
                pair_address = "0x" + result['result'][-40:]
                if pair_address != "0x0000000000000000000000000000000000000000":
                    return pair_address.lower()
            return None
        except:
            return None

    def get_token_transfers(self, contract_address):
        """获取代币的转账记录"""
        params = {
            'module': 'account',
            'action': 'tokentx',
            'contractaddress': contract_address,
            'page': 1,
            'offset': 100,
            'sort': 'desc',
            'apikey': self.etherscan_api_key
        }

        try:
            response = requests.get(self.etherscan_base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == '1' and data['message'] == 'OK':
                # 尝试获取pair地址
                pair_address = self.get_pair_address(contract_address)
                
                return {
                    'transfers': data['result'],
                    'pair_address': pair_address
                }
            else:
                print(f"API Error: {data['message']}")
                return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching transfers: {e}")
            return None

    def get_token_price(self, chain_id, token_address):
        """从DexScreener获取代币价格信息"""
        url = f"{self.dexscreener_base_url}/pairs/{chain_id}/{token_address}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            if 'pairs' in data and data['pairs']:
                return data['pairs'][0]
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching price info: {e}")
            return None

    def get_token_balance(self, address, contract_address, block_number):
        """获取指定区块时某地址的代币余额"""
        params = {
            'module': 'account',
            'action': 'tokenbalance',
            'contractaddress': contract_address,
            'address': address,
            'tag': hex(int(block_number)),
            'apikey': self.etherscan_api_key
        }

        try:
            response = requests.get(self.etherscan_base_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data['status'] == '1' and data['message'] == 'OK':
                return int(data['result'])
            return 0
        except:
            return 0

    def get_transaction_logs(self, tx_hash):
        """获取交易的事件日志"""
        params = {
            'module': 'proxy',
            'action': 'eth_getTransactionReceipt',
            'txhash': tx_hash,
            'apikey': self.etherscan_api_key
        }

        try:
            response = requests.get(self.etherscan_base_url, params=params)
            response.raise_for_status()
            data = response.json()
            if data['result']:
                return data['result']['logs']
            return None
        except:
            return None

    def determine_transaction_type(self, tx, token_address):
        """通过事件日志确定交易类型"""
        logs = self.get_transaction_logs(tx['hash'])
        if not logs:
            return None, 0

        token_address = token_address.lower()
        user_address = tx['from'].lower()
        
        # 查找Swap事件的签名
        swap_topic = '0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822'  # Uniswap V2 Swap
        
        token_transfers = []
        swap_found = False
        
        for log in logs:
            # 检查是否是Swap事件
            if log.get('topics') and log['topics'][0] == swap_topic:
                swap_found = True
            
            # 检查Transfer事件
            if log.get('topics') and log['topics'][0] == '0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef':
                from_addr = '0x' + log['topics'][1][-40:]
                to_addr = '0x' + log['topics'][2][-40:]
                token_contract = log['address'].lower()
                
                if token_contract == token_address:
                    amount = int(log['data'], 16)
                    token_transfers.append({
                        'from': from_addr.lower(),
                        'to': to_addr.lower(),
                        'amount': amount
                    })
        
        # 如果找到了Swap事件，说明这是一次交易所交易
        if swap_found and token_transfers:
            # 找到用户参与的第一笔转账
            for transfer in token_transfers:
                if transfer['from'] == user_address:
                    return "SELL", transfer['amount']
                elif transfer['to'] == user_address:
                    return "BUY", transfer['amount']
        
        return None, 0

    def format_transactions(self, data, decimals=18):
        """格式化交易信息"""
        if not data or not data['transfers']:
            return
        
        transfers = data['transfers']
        pair_address = data['pair_address']
        
        print("\nTransaction History:")
        print("{:<25}{:<10}{:<20}{:<42}".format("Time", "Type", "Tokens", "Wallet Address"))
        print("-" * 90)
        
        # 如果没有pair_address，显示所有转账记录
        if not pair_address:
            for tx in transfers:
                timestamp = datetime.fromtimestamp(int(tx['timeStamp']))
                tokens = float(tx['value']) / (10 ** decimals)
                
                print("{:<25}{:<10}{:<20.4f}{:<42}".format(
                    str(timestamp),
                    "TRANSFER",
                    tokens,
                    tx['to']
                ))
            return
        
        # 如果有pair_address，只显示与流动性池的交易
        for tx in transfers:
            timestamp = datetime.fromtimestamp(int(tx['timeStamp']))
            from_addr = tx['from'].lower()
            to_addr = tx['to'].lower()
            
            # 通过流动性池地址判断交易类型
            if from_addr == pair_address:
                txn_type = "BUY"
                wallet = to_addr
            elif to_addr == pair_address:
                txn_type = "SELL"
                wallet = from_addr
            else:
                continue  # 跳过非交易所交易
            
            # 计算代币数量
            tokens = float(tx['value']) / (10 ** decimals)
            
            print("{:<25}{:<10}{:<20.4f}{:<42}".format(
                str(timestamp),
                txn_type,
                tokens,
                wallet
            ))

def main():
    api = TokenTransactions()
    
    while True:
        token_address = input("\nEnter token contract address: ")
        
        print("\nFetching data...")
        # 获取价格信息
        price_info = api.get_token_price('ethereum', token_address)
        if price_info:
            print(f"\nToken: {price_info['baseToken']['symbol']}")
            print(f"Current Price: ${float(price_info['priceUsd']):.8f}")
            print(f"24h Volume: ${price_info['volume']['h24']:.2f}")
            print(f"Pair Address: {price_info['pairAddress']}")
        
        # 获取交易历史
        data = api.get_token_transfers(token_address)
        if data:
            # 获取代币精度
            decimals = int(data['transfers'][0]['tokenDecimal'])
            api.format_transactions(data, decimals)
        else:
            print("No transaction history found")
        
        again = input("\nWould you like to check another token? (y/n): ")
        if again.lower() != 'y':
            break

if __name__ == "__main__":
    main() 