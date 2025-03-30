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