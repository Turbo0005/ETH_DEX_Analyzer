# ETH DEX Scanner

一个用于分析以太坊代币交易的工具，主要用于追踪代币在 Uniswap V2 上的交易情况。

## 功能特点

1. 代币信息查询
   - 当前价格
   - 24小时交易量
   - 流动性池地址
   - 代币符号

2. 交易记录分析
   - 自动识别交易类型（买入/卖出）
   - 显示交易时间戳
   - 计算交易代币数量
   - 记录交易钱包地址

3. 智能合约交互
   - 自动获取 Uniswap V2 流动性池地址
   - 支持代币余额查询
   - 解析交易事件日志

## 使用方法

### 前期准备
1. 获取 Etherscan API Key
   - 访问 https://etherscan.io/apis
   - 注册并创建 API Key
   - 将 API Key 填入代码中的 `YOUR_ETHERSCAN_API_KEY`

### 运行程序
1. 输入代币合约地址
2. 等待程序获取数据
3. 查看分析结果：
   - 代币基本信息
   - 交易历史记录

### 输出信息
```
Token: XXX
Current Price: $X.XXXXXXXX
24h Volume: $XXX.XX
Pair Address: 0x...

Transaction History:
Time                     Type       Tokens              Wallet Address
-------------------------------------------------------------------------
YYYY-MM-DD HH:MM:SS     BUY        XXX.XXXX           0x...
YYYY-MM-DD HH:MM:SS     SELL       XXX.XXXX           0x...
```

## 技术细节

### 交易类型判断
1. 通过流动性池地址判断：
   - 从池子流出 = 买入（BUY）
   - 流入池子 = 卖出（SELL）

2. 通过事件日志判断：
   - 分析 Swap 事件
   - 分析 Transfer 事件
   - 追踪代币流向

### API 使用
1. Etherscan API
   - 获取代币转账记录
   - 查询合约事件日志
   - 获取代币余额

2. DexScreener API
   - 获取实时价格信息
   - 获取交易量数据

## 注意事项

1. API 限制
   - Etherscan API 有调用频率限制
   - 建议适当控制请求频率

2. 合约地址
   - 需要输入正确的代币合约地址
   - 地址格式：0x + 40位十六进制字符

3. 交易记录
   - 默认只显示最近100条记录
   - 只显示与流动性池的交易
   - 普通转账不会显示

4. 价格信息
   - 依赖 DexScreener 的数据
   - 可能存在短暂的延迟

## 依赖库
- requests
- datetime 