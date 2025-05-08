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
) COMMENT='指数日线行情表';


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

-- 账户持仓
CREATE TABLE IF NOT EXISTS account_position (
    id INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键ID',
    exchange_id VARCHAR(32) NOT NULL COMMENT '交易所',
    account_id VARCHAR(32) NOT NULL COMMENT '账户ID',
    symbol_id VARCHAR(32) NOT NULL COMMENT '标的代码',
    position_side VARCHAR(32) NOT NULL COMMENT '持仓方向',
    position DECIMAL(18, 4) NOT NULL COMMENT '持仓数量',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (account_id, symbol_id)
) COMMENT='账户持仓表';




-- 存储资金费率套利策略使用的交易对白名单信息
CREATE TABLE IF NOT EXISTS `funding_rate_arbitrage_whitelist` (
    `exchange_id` VARCHAR(32) NOT NULL COMMENT '交易所',
    `base_currency` VARCHAR(10) COMMENT '基础货币 (例如: BTC)',
    `quote_currency` VARCHAR(10) COMMENT '计价货币 (例如: USDT)',
    `spot_inst_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '现货交易对ID (例如: BTC-USDT)',
    `swap_inst_id` VARCHAR(50) NOT NULL UNIQUE COMMENT '永续合约交易对ID (例如: BTC-USDT-SWAP)',


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

    `is_active` BOOLEAN NOT NULL DEFAULT TRUE COMMENT '该交易对是否处于活跃白名单状态 (TRUE: 活跃, FALSE: 暂停)',
    `comment` TEXT COMMENT '人工审核或系统添加的备注信息',

    `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    UNIQUE KEY (exchange_id, base_currency, quote_currency),
    INDEX `idx_is_active` (`is_active`)
) COMMENT='资金费率套利交易对白名单';





