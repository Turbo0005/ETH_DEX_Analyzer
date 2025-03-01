import requests
from datetime import datetime, timedelta
import time
import re
from eth_dex_scanner import TokenTransactions

class WalletAnalyzer:
    def __init__(self):
        # 在此处填写自己的 Etherscan API Key
        # 获取 API Key: https://etherscan.io/apis
        self.token_api = TokenTransactions()

    def parse_relative_time(self, time_str):
        """解析相对时间字符串，如 1d, 2h, 30m"""
        # 处理 "now" 关键字
        if time_str.lower() == 'now':
            return datetime.now()

        units = {
            'm': 'minutes',
            'h': 'hours',
            'd': 'days',
            'w': 'weeks'
        }
        
        pattern = r'(\d+)([mhdw])'
        match = re.match(pattern, time_str.lower())
        
        if match:
            value, unit = match.groups()
            if unit in units:
                kwargs = {units[unit]: int(value)}
                # 从现在开始往前计算
                return datetime.now() - timedelta(**kwargs)
        return None

    def parse_time_str(self, time_str):
        """解析多种格式的时间字符串"""
        formats = [
            '%Y-%m-%d %H:%M:%S',  # 2025-02-28 18:30:00
            '%Y-%m-%d %H:%M',     # 2025-02-28 18:30
            '%Y-%m-%d',           # 2025-02-28
            '%m-%d %H:%M',        # 02-28 18:30
            '%H:%M'               # 18:30
        ]

        # 处理相对时间
        relative_time = self.parse_relative_time(time_str)
        if relative_time:
            return relative_time

        # 处理具体时间
        time_str = time_str.strip()
        
        # 如果只有时间，添加今天的日期
        if len(time_str) <= 5 and ':' in time_str:
            time_str = f"{datetime.now().strftime('%Y-%m-%d')} {time_str}"
        # 如果只有月日和时间，添加当年
        elif len(time_str) <= 11 and ':' in time_str:
            time_str = f"{datetime.now().year}-{time_str}"

        for fmt in formats:
            try:
                return datetime.strptime(time_str, fmt)
            except ValueError:
                continue
        return None

    def parse_time_ranges(self, time_ranges_str):
        """解析时间段字符串"""
        ranges = []
        for range_str in time_ranges_str.split('/'):
            try:
                # 处理单个时间点（默认范围为前后1小时）
                if ' to ' not in range_str:
                    point = self.parse_time_str(range_str.strip())
                    if point:
                        start_time = point - timedelta(hours=1)
                        end_time = point + timedelta(hours=1)
                        ranges.append((int(start_time.timestamp()), int(end_time.timestamp())))
                        continue
                
                # 处理时间范围
                start_str, end_str = range_str.strip().split(' to ')
                start_time = self.parse_time_str(start_str)
                end_time = self.parse_time_str(end_str)
                
                if start_time and end_time:
                    # 确保开始时间早于结束时间
                    if start_time > end_time:
                        start_time, end_time = end_time, start_time
                    ranges.append((int(start_time.timestamp()), int(end_time.timestamp())))
                else:
                    print(f"Error parsing time range: {range_str}")
                    continue
                    
            except Exception as e:
                print(f"Error parsing time range: {range_str}")
                print(f"Please use one of these formats:")
                print("- YYYY-MM-DD HH:MM:SS")
                print("- YYYY-MM-DD HH:MM")
                print("- YYYY-MM-DD")
                print("- MM-DD HH:MM")
                print("- HH:MM")
                print("- Relative time: 1d, 2h, 30m, 1w")
                print("- 'now' for current time")
                return None
        return ranges

    def get_transactions_in_ranges(self, token_address, time_ranges):
        """获取指定时间段内的交易"""
        # 验证合约地址格式
        if not re.match(r'^0x[a-fA-F0-9]{40}$', token_address):
            print("Error: Invalid contract address format")
            return None

        data = self.token_api.get_token_transfers(token_address)
        if not data:
            print("\nFailed to fetch transactions. Possible reasons:")
            print("1. Invalid contract address")
            print("2. API rate limit exceeded")
            print("3. Network connection issue")
            print("\nTry again in a few minutes or check the contract address")
            return None

        if not data['transfers']:
            print("No transactions found for this token")
            return None

        # 获取pair地址和交易记录
        transfers = data['transfers']
        pair_address = data['pair_address']
        if not pair_address:
            print("\nWarning: Could not find Uniswap V2 liquidity pool address")
            print("This might be because:")
            print("1. Token is not listed on Uniswap V2")
            print("2. Token uses a different DEX")
            print("3. Token contract address is incorrect")
            return None

        # 按时间段整理交易记录
        range_transactions = {i: [] for i in range(len(time_ranges))}
        
        for tx in transfers:
            timestamp = int(tx['timeStamp'])
            from_addr = tx['from'].lower()
            to_addr = tx['to'].lower()

            # 判断交易类型
            if from_addr == pair_address:
                txn_type = "BUY"
                wallet = to_addr
            elif to_addr == pair_address:
                txn_type = "SELL"
                wallet = from_addr
            else:
                continue

            # 检查是否在任一时间段内
            for i, (start, end) in enumerate(time_ranges):
                if start <= timestamp <= end:
                    range_transactions[i].append({
                        'wallet': wallet,
                        'type': txn_type,
                        'timestamp': timestamp,
                        'amount': float(tx['value']) / (10 ** int(tx['tokenDecimal']))
                    })

        # 检查是否找到任何交易
        total_transactions = sum(len(txs) for txs in range_transactions.values())
        if total_transactions == 0:
            print("\nNo transactions found in the specified time ranges")
            return None

        return range_transactions

    def find_active_wallets(self, range_transactions, min_ranges=2):
        """找出在多个时间段内都有交易的钱包"""
        wallet_activity = {}
        
        # 统计每个钱包在不同时间段的活动
        for range_idx, transactions in range_transactions.items():
            for tx in transactions:
                wallet = tx['wallet']
                if wallet not in wallet_activity:
                    wallet_activity[wallet] = set()
                wallet_activity[wallet].add(range_idx)

        # 筛选出在足够多时间段内活跃的钱包
        active_wallets = {
            wallet: ranges 
            for wallet, ranges in wallet_activity.items() 
            if len(ranges) >= min_ranges
        }

        return active_wallets

    def display_results(self, active_wallets, range_transactions):
        """显示分析结果"""
        if not active_wallets:
            print("\nNo wallets found active in multiple time ranges.")
            # 添加更多诊断信息
            print("\nDiagnostic information:")
            for range_idx, transactions in range_transactions.items():
                print(f"Range {range_idx} has {len(transactions)} transactions")
                if transactions:
                    wallets = set(tx['wallet'] for tx in transactions)
                    print(f"Unique wallets in this range: {len(wallets)}")
            return

        print("\nWallets active in multiple time ranges:")
        print("-" * 80)
        
        for wallet, ranges in active_wallets.items():
            print(f"\nWallet: {wallet}")
            print(f"Active in {len(ranges)} time ranges: {sorted(ranges)}")
            print("\nDetailed transactions:")
            
            for range_idx in ranges:
                transactions = [
                    tx for tx in range_transactions[range_idx]
                    if tx['wallet'] == wallet
                ]
                
                print(f"\nRange {range_idx}:")
                for tx in transactions:
                    timestamp = datetime.fromtimestamp(tx['timestamp'])
                    print(f"Time: {timestamp}, Type: {tx['type']}, Amount: {tx['amount']:.4f}")
            print("-" * 40)

def main():
    analyzer = WalletAnalyzer()
    
    token_address = input("Enter token contract address: ")
    print("\nTime format options:")
    print("1. Absolute time: YYYY-MM-DD HH:MM:SS, YYYY-MM-DD HH:MM, YYYY-MM-DD, MM-DD HH:MM, HH:MM")
    print("2. Relative time: 1d (1 day ago), 2h (2 hours ago), 30m (30 minutes ago), 1w (1 week ago)")
    print("3. Time range: <time1> to <time2>")
    print("4. Multiple ranges: separate with /")
    print("\nExamples:")
    print("- 2d to 1d")
    print("- 2025-02-28 18:30")
    print("- 02-28 18:30 to 03-01 18:30")
    print("- 1w to 6d/3d to 2d/1d to now")
    
    time_ranges_str = input("\nEnter time ranges: ")

    # 解析时间段
    time_ranges = analyzer.parse_time_ranges(time_ranges_str)
    if not time_ranges:
        return

    print("\nAnalyzing transactions for these time ranges:")
    for i, (start, end) in enumerate(time_ranges):
        print(f"Range {i}: {datetime.fromtimestamp(start)} to {datetime.fromtimestamp(end)}")

    print("\nFetching and analyzing transactions...")
    
    # 获取交易记录
    range_transactions = analyzer.get_transactions_in_ranges(token_address, time_ranges)
    if not range_transactions:
        print("No transactions found")
        return

    # 查找活跃钱包
    active_wallets = analyzer.find_active_wallets(range_transactions)
    
    # 显示结果
    analyzer.display_results(active_wallets, range_transactions)

if __name__ == "__main__":
    main() 