-- 套利
CREATE TABLE IF NOT EXISTS arbitrage_position (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    symbol_id VARCHAR(32) NOT NULL COMMENT '合约代码',
    exchange_1 VARCHAR(32) NOT NULL COMMENT '买入交易所',
    exchange_2 VARCHAR(32) NOT NULL COMMENT '卖出交易所',
    leg_1_direction VARCHAR(32) NOT NULL COMMENT '买入方向',
    leg_2_direction VARCHAR(32) NOT NULL COMMENT '卖出方向',
    leg_1_price DECIMAL(18, 4) NOT NULL COMMENT '买入价格',
    leg_2_price DECIMAL(18, 4) NOT NULL COMMENT '卖出价格',
    leg_1_volume DECIMAL(18, 4) NOT NULL COMMENT '买入数量',
    leg_2_volume DECIMAL(18, 4) NOT NULL COMMENT '卖出数量',
    pre_close DECIMAL(18, 4) COMMENT '前收盘价',
    volume BIGINT COMMENT '成交量',
    turnover DECIMAL(24, 4) COMMENT '成交额',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (trade_date, index_code)
) COMMENT='套利持仓表';


-- 黑名单交易对
CREATE TABLE IF NOT EXISTS blacklist_symbols (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    symbol_id VARCHAR(32) NOT NULL COMMENT '合约代码',
    exchange_id VARCHAR(32) NULL COMMENT '交易所ID, 如果为空, 则表示所有交易所',
    strategy_name VARCHAR(32) NULL COMMENT '策略名称, 如果为空, 则表示所有策略',
    reason VARCHAR(128) NULL COMMENT '禁止原因',
    active BOOLEAN DEFAULT TRUE COMMENT '是否生效',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (symbol_id, exchange_id, strategy_name, reason)
) COMMENT='黑名单交易对表';


-- 跨交易所套利信号
CREATE TABLE IF NOT EXISTS cross_exchange_arbitrage_signal (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    signal_date DATE NOT NULL COMMENT '信号日期',
    signal_time TIME NOT NULL COMMENT '信号时间',
    symbol_id VARCHAR(32) NOT NULL COMMENT '合约代码',
    exchange_1 VARCHAR(32) NULL COMMENT '交易所1',
    exchange_2 VARCHAR(32) NULL COMMENT '交易所2',
    leg_1_bid DECIMAL(18, 4) NULL COMMENT '交易所1买一价',
    leg_1_bid_volume DECIMAL(18, 4) NULL COMMENT '交易所1买一量',
    leg_1_ask DECIMAL(18, 4) NULL COMMENT '交易所1卖一价',
    leg_1_ask_volume DECIMAL(18, 4) NULL COMMENT '交易所1卖一量',
    leg_2_bid DECIMAL(18, 4) NULL COMMENT '交易所2买一价',
    leg_2_bid_volume DECIMAL(18, 4) NULL COMMENT '交易所2买一量',
    leg_2_ask DECIMAL(18, 4) NULL COMMENT '交易所2卖一价',
    leg_2_ask_volume DECIMAL(18, 4) NULL COMMENT '交易所2卖一量',
    hedge_exchange VARCHAR(32) NULL COMMENT '对冲交易所',
    hedge_symbol_id VARCHAR(32) NULL COMMENT '对冲合约代码',
    hedge_contract_size DECIMAL(18, 4) NULL COMMENT '对冲合约乘数',
    hedge_bid DECIMAL(18, 4) NULL COMMENT '对冲交易所买一价',
    hedge_bid_volume DECIMAL(18, 4) NULL COMMENT '对冲交易所买一量',
    hedge_ask DECIMAL(18, 4) NULL COMMENT '对冲交易所卖一价',
    hedge_ask_volume DECIMAL(18, 4) NULL COMMENT '对冲交易所卖一量',
    spread DECIMAL(18, 4) NULL COMMENT '价差',
    spread_ratio DECIMAL(18, 4) NULL COMMENT '价差比例',
    status VARCHAR(32) NULL COMMENT '状态',
    remark VARCHAR(128) NULL COMMENT '备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (symbol_id, signal_date, signal_time)
) COMMENT='跨交易所套利信号表';

-- 跨交易所套利对冲订单(母单)
CREATE TABLE IF NOT EXISTS cross_exchange_arbitrage_hedge_order (
    order_id VARCHAR(32) NOT NULL COMMENT '订单ID',
    order_date DATE NOT NULL COMMENT '订单日期',
    order_time TIME NOT NULL COMMENT '订单时间',
    symbol_id VARCHAR(32) NOT NULL COMMENT '合约代码',
    -- 第1腿
    leg1_exchange VARCHAR(32) NOT NULL COMMENT '第1腿交易所',
    leg1_price DECIMAL(18, 4) NOT NULL COMMENT '第1腿买入价格',
    leg1_volume DECIMAL(18, 4) NOT NULL COMMENT '第1腿买入数量',
    -- 第2腿
    leg2_exchange VARCHAR(32) NOT NULL COMMENT '第2腿交易所',
    leg2_price DECIMAL(18, 4) NOT NULL COMMENT '第2腿卖出价格',
    leg2_volume DECIMAL(18, 4) NOT NULL COMMENT '第2腿卖出数量',
    -- 对冲订单
    hedge_exchange VARCHAR(32) NOT NULL COMMENT '对冲交易所',
    hedge_contract_id VARCHAR(32) NOT NULL COMMENT '对冲合约代码',
    hedge_contract_size DECIMAL(18, 4) NOT NULL COMMENT '对冲合约乘数',
    hedge_price DECIMAL(18, 4) NOT NULL COMMENT '对冲价格',
    hedge_volume DECIMAL(18, 4) NOT NULL COMMENT '对冲数量',

    signal_id INT NOT NULL COMMENT '信号ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (order_id)
) COMMENT='跨交易所套利对冲订单表';

-- 跨交易所套利订单明细
CREATE TABLE IF NOT EXISTS cross_exchange_arbitrage_order_detail (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    order_id VARCHAR(32) NOT NULL COMMENT '订单ID',
    order_date DATE NOT NULL COMMENT '订单日期',
    order_time TIME NOT NULL COMMENT '订单时间',
    leg_type VARCHAR(32) NOT NULL COMMENT '腿类型, leg1, leg2, hedge', 
    exchange VARCHAR(32) NOT NULL COMMENT '交易所',
    symbol_id VARCHAR(32) NOT NULL COMMENT '合约代码',
    price DECIMAL(18, 4) NOT NULL COMMENT '价格',
    volume DECIMAL(18, 4) NOT NULL COMMENT '数量',
    volume_trade DECIMAL(18, 4) NOT NULL COMMENT '成交数量',
    direction VARCHAR(32) NOT NULL COMMENT '方向',
    offset VARCHAR(32) NOT NULL COMMENT '开平仓',
    order_type VARCHAR(32) NOT NULL COMMENT '订单类型',
    order_status VARCHAR(32) NOT NULL COMMENT '订单状态',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (order_id)
) COMMENT='跨交易所套利订单明细表';

-- 跨交易所套利持仓
CREATE TABLE IF NOT EXISTS cross_exchange_arbitrage_position (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    symbol_id VARCHAR(32) NOT NULL COMMENT '币对代码',
    -- 第1腿, 多头现货持仓
    leg1_exchange VARCHAR(32) NOT NULL COMMENT '第1腿交易所',
    leg1_position DECIMAL(18, 4) NOT NULL COMMENT '第1腿持仓数量',
    leg1_frozen DECIMAL(18, 4) NOT NULL COMMENT '第1腿冻结',
    -- 第2腿, 多头现货持仓
    leg2_exchange VARCHAR(32) NOT NULL COMMENT '第2腿交易所',
    leg2_position DECIMAL(18, 4) NOT NULL COMMENT '第2腿持仓数量',
    leg2_frozen DECIMAL(18, 4) NOT NULL COMMENT '第2腿冻结',
    -- 对冲仓位，空头永续合约持仓
    hedge_exchange VARCHAR(32) NOT NULL COMMENT '对冲交易所',
    hedge_contract_id VARCHAR(32) NOT NULL COMMENT '对冲合约代码',
    hedge_contract_size DECIMAL(18, 4) NOT NULL COMMENT '对冲合约乘数',
    hedge_position DECIMAL(18, 4) NOT NULL COMMENT '对冲持仓数量',
    hedge_frozen DECIMAL(18, 4) NOT NULL COMMENT '对冲冻结',

    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (symbol_id)
) COMMENT='跨交易所套利持仓表';

-- 账户资产(持有币种)
CREATE TABLE IF NOT EXISTS balance (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    exchange_id VARCHAR(32) NOT NULL COMMENT '交易所',
    symbol_id VARCHAR(32) NOT NULL COMMENT '标的代码',
    total DECIMAL(18, 4) NOT NULL COMMENT '总资产',
    available DECIMAL(18, 4) NOT NULL COMMENT '可用资产',
    frozen DECIMAL(18, 4) NOT NULL COMMENT '冻结资产',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (exchange_id, account_id, symbol_id)
) COMMENT='账户资产表';

-- 持仓表(合约持仓)
CREATE TABLE IF NOT EXISTS position (
    `id` INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    `exchange_id` VARCHAR(32) NOT NULL COMMENT '交易所ID',
    `symbol_id` VARCHAR(32) NOT NULL COMMENT '交易对ID',
    `notional` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '名义价值(美元)',
    `margin_mode` VARCHAR(16) NOT NULL COMMENT '保证金模式(cross/isolated)',
    `liquidation_price` DECIMAL(20,8) COMMENT '强平价格',
    `entry_price` DECIMAL(20,8) NOT NULL COMMENT '开仓均价',
    `unrealized_pnl` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '未实现盈亏',
    `realized_pnl` DECIMAL(20,8) NOT NULL DEFAULT 0 COMMENT '已实现盈亏',
    `pnl_percentage` DECIMAL(10,4) COMMENT '收益百分比',
    `contracts` DECIMAL(20,8) NOT NULL COMMENT '合约数量',
    `contract_size` DECIMAL(20,8) NOT NULL COMMENT '合约面值',
    `mark_price` DECIMAL(20,8) NOT NULL COMMENT '标记价格',
    `side` VARCHAR(16) NOT NULL COMMENT '持仓方向(long/short)',
    `maintenance_margin` DECIMAL(20,8) NOT NULL COMMENT '维持保证金',
    `maintenance_margin_percentage` DECIMAL(10,4) NOT NULL COMMENT '维持保证金比例',
    `collateral` DECIMAL(20,8) NOT NULL COMMENT '抵押品价值',
    `initial_margin` DECIMAL(20,8) NOT NULL COMMENT '初始保证金',
    `initial_margin_percentage` DECIMAL(10,4) NOT NULL COMMENT '初始保证金比例',
    `leverage` INT NOT NULL COMMENT '杠杆倍数',
    `margin_ratio` DECIMAL(10,4) NOT NULL COMMENT '保证金率',
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (exchange_id, symbol_id)
) COMMENT='持仓表';


-- 存储资金费率套利策略使用的交易对白名单信息
CREATE TABLE IF NOT EXISTS `funding_rate_arbitrage_whitelist` (
    `exchange_id` VARCHAR(32) NOT NULL COMMENT '交易所',
    `base_currency` VARCHAR(10) COMMENT '基础货币 (例如: BTC)',
    `quote_currency` VARCHAR(10) COMMENT '计价货币 (例如: USDT)',
    `spot_inst_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '现货交易对ID (例如: BTC-USDT)',
    `swap_inst_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '永续合约交易对ID (例如: BTC-USDT-SWAP)',


    `is_active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '该交易对是否处于活跃白名单状态 (TRUE: 活跃, FALSE: 暂停)',
    `comment` TEXT COMMENT '人工审核或系统添加的备注信息',

    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (exchange_id, base_currency, quote_currency),
    INDEX `idx_is_active` (`is_active`)
) COMMENT='资金费率套利交易对白名单';



-- 存储资金费率分析指标
CREATE TABLE IF NOT EXISTS `funding_rate_basis_summary` (
    `exchange_id` VARCHAR(32) NOT NULL COMMENT '交易所',
    `base_currency` VARCHAR(10) COMMENT '基础货币 (例如: BTC)',
    `quote_currency` VARCHAR(10) COMMENT '计价货币 (例如: USDT)',

    -- 以下字段可以用来存储筛选器生成的分析结果，供人工审核参考
    `avg_ann_funding_rate_90d` DECIMAL(10, 4) COMMENT '过去90天平均年化资金费率 (%)',
    `median_ann_funding_rate_90d` DECIMAL(10, 4) COMMENT '过去90天中位数年化资金费率 (%)',
    `std_dev_ann_funding_rate_90d` DECIMAL(10, 4) COMMENT '过去90天年化资金费率标准差 (%)',
    `positive_rate_pct_90d` DECIMAL(5, 2) COMMENT '过去90天资金费率为正的百分比 (%)',
    
    -- 基差分析相关字段
    `avg_basis_90d` DECIMAL(10, 4) COMMENT '过去90天合约与现货的平均基差 (%)',
    `median_basis_90d` DECIMAL(10, 4) COMMENT '过去90天合约与现货的中位数基差 (%)',
    `std_dev_basis_90d` DECIMAL(10, 4) COMMENT '过去90天基差标准差 (%)',
    `max_basis_90d` DECIMAL(10, 4) COMMENT '过去90天最大基差 (%)',
    `min_basis_90d` DECIMAL(10, 4) COMMENT '过去90天最小基差 (%)',
    `basis_quartile_1_90d` DECIMAL(10, 4) COMMENT '过去90天基差第一四分位数 (%)',
    `basis_quartile_3_90d` DECIMAL(10, 4) COMMENT '过去90天基差第三四分位数 (%)',
    `basis_volatility_90d` DECIMAL(10, 4) COMMENT '过去90天基差波动率 (%)',
    `positive_basis_pct_90d` DECIMAL(5, 2) COMMENT '过去90天基差为正的百分比 (%)',
    
    -- 基差与资金费率相关性分析
    `basis_funding_correlation_90d` DECIMAL(5, 4) COMMENT '过去90天基差与资金费率的相关系数',
    `avg_basis_to_funding_ratio_90d` DECIMAL(10, 4) COMMENT '过去90天平均基差/资金费率比值',
    
    -- 基差策略潜在收益分析
    `potential_apr_90d` DECIMAL(10, 4) COMMENT '基于过去90天数据计算的潜在年化收益率 (%)',
    `sharpe_ratio_90d` DECIMAL(10, 4) COMMENT '过去90天基差套利的夏普比率',
    `max_drawdown_90d` DECIMAL(10, 4) COMMENT '过去90天基差策略的最大回撤 (%)',

    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (exchange_id, base_currency, quote_currency)
) COMMENT='资金费率分析指标表';


-- 资金费率套利持仓
CREATE TABLE IF NOT EXISTS funding_rate_arbitrage_position (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    exchange_id VARCHAR(32) NOT NULL COMMENT '交易所ID',
    symbol_id VARCHAR(32) NOT NULL COMMENT '交易对代码',
    -- 交易对信息
    spot_inst_id VARCHAR(50) NOT NULL COMMENT '现货交易对ID',
    swap_inst_id VARCHAR(50) NOT NULL COMMENT '永续合约交易对ID',
    swap_contract_size DECIMAL(18, 4) NOT NULL COMMENT '永续合约乘数',
    -- 持仓信息
    arbitrage_position DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '套利头寸',
    spot_position DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '现货持仓数量',  
    swap_position DECIMAL(18, 4) NOT NULL DEFAULT 0 COMMENT '永续持仓数量',
    -- 持仓状态
    status VARCHAR(32) NOT NULL DEFAULT 'OPENING' COMMENT '持仓状态(OPENING: 正在开仓, FAILED: 开仓失败, HOLDING: 持有中, CLOSING: 平仓中, CLOSED: 已平仓)',
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    -- 唯一索引（账户+现货+永续交易对）
    UNIQUE KEY (exchange_id, symbol_id)
) COMMENT='资金费率套利持仓表';



-- 资金费率套利信号
CREATE TABLE IF NOT EXISTS funding_rate_arbitrage_signal (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    signal_date DATE NOT NULL COMMENT '信号日期',
    signal_time TIME NOT NULL COMMENT '信号时间',
    exchange_id VARCHAR(32) NOT NULL COMMENT '交易所ID',
    symbol_id VARCHAR(32) NOT NULL COMMENT '货币对代码（如BTC/USDT）',
    spot_inst_id VARCHAR(50) NOT NULL COMMENT '现货交易对ID',
    swap_inst_id VARCHAR(50) NOT NULL COMMENT '永续合约交易对ID',
    swap_contract_size DECIMAL(18, 4) NOT NULL COMMENT '永续合约乘数',
    
    -- 资金费率核心指标
    current_funding_rate DECIMAL(10, 6) NOT NULL COMMENT '当前资金费率（原始值，如0.0001表示0.01%）',
    annualized_funding_rate DECIMAL(10, 4) NOT NULL COMMENT '年化资金费率（%，如5.00表示5%）',
    
    -- 现货与永续价格数据
    spot_bid DECIMAL(18, 4) NOT NULL COMMENT '现货买一价',
    spot_bid_volume DECIMAL(18, 4) NOT NULL COMMENT '现货买一量',
    spot_ask DECIMAL(18, 4) NOT NULL COMMENT '现货卖一价',
    spot_ask_volume DECIMAL(18, 4) NOT NULL COMMENT '现货卖一量',
    swap_bid DECIMAL(18, 4) NOT NULL COMMENT '永续买一价',
    swap_bid_volume DECIMAL(18, 4) NOT NULL COMMENT '永续买一量',
    swap_ask DECIMAL(18, 4) NOT NULL COMMENT '永续卖一价',
    swap_ask_volume DECIMAL(18, 4) NOT NULL COMMENT '永续卖一量',
    
    -- 基差计算结果
    basis DECIMAL(10, 4) NOT NULL COMMENT '基差（永续-现货价格，绝对值）',
    basis_ratio DECIMAL(10, 4) NOT NULL COMMENT '基差比例（%，(永续价格-现货价格)/现货价格*100）',
    
    -- 信号状态与备注
    status VARCHAR(32) NOT NULL DEFAULT 'generated' COMMENT '信号状态（generated: 已生成, triggered: 已触发交易, expired: 已失效）',
    remark VARCHAR(256) NULL COMMENT '备注（如异常说明、触发条件等）',
    
    -- 时间戳
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '记录更新时间',
    
    -- 唯一索引（同一时间同一交易对仅一条信号）
    UNIQUE KEY (signal_date, signal_time, exchange_id, symbol_id)
) COMMENT='资金费率套利信号表';


