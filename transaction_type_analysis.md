# 判断交易类型（买入/卖出）的演进思路

## 1. Version 1 - 基于合约地址判断
```python
# 判断交易方向
is_buy = tx['to'].lower() == tx['contractAddress'].lower()
txn_type = "SELL" if is_buy else "BUY"
```
问题：直接与代币合约地址比较是不准确的，因为交易实际是与流动性池进行交互

## 2. Version 2 - 分析事件日志
```python
# 检查Transfer事件和Swap事件
if log['topics'][0] == swap_topic:  # Uniswap V2 Swap事件
    swap_found = True
if log['topics'][0] == transfer_topic:  # Transfer事件
    # 记录代币转账信息
    token_transfers.append({
        'from': from_addr.lower(),
        'to': to_addr.lower(),
        'amount': amount
    })
```
问题：一次交易中可能有多个Transfer事件，导致同一笔交易被显示多次

## 3. Version 3 - 检查余额变化
```python
# 获取交易前后的代币余额
balance_before = self.get_token_balance(wallet, contract_address, block_number - 1)
balance_after = self.get_token_balance(wallet, contract_address, block_number)

# 通过余额变化判断交易类型
if balance_after > balance_before:
    txn_type = "BUY"
elif balance_after < balance_before:
    txn_type = "SELL"
```
问题：需要额外的API调用来获取历史余额，会降低程序运行速度

## 4. Version 4 - 基于流动性池地址判断
```python
# 获取Uniswap V2流动性池地址
pair_address = self.get_pair_address(token_address)

# 通过与流动性池的交互方向判断交易类型
if from_addr == pair_address:
    txn_type = "BUY"     # 从池子流出 = 买入
    wallet = to_addr
elif to_addr == pair_address:
    txn_type = "SELL"    # 流入池子 = 卖出
    wallet = from_addr
```

### Version 4 的优点：
1. 准确性高：直接判断与流动性池的交互方向
2. 性能好：不需要分析复杂的事件日志
3. 逻辑清晰：从池子流出是买入，流入池子是卖出
4. 可扩展：可以支持其他DEX的流动性池

### Version 4 的实现细节：
1. 使用Uniswap V2 Factory合约获取准确的pair地址
2. 只处理与流动性池相关的交易
3. 跳过非交易所交易（普通转账等）

### Version 4 的注意事项：
1. 需要正确配置Factory合约地址
2. 默认使用WETH作为交易对
3. 需要处理找不到pair地址的情况


        