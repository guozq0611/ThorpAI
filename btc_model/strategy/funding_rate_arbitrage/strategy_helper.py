class StrategyHelper:
    def __init__(self):
        pass

    @staticmethod
    def calculate_avg_ann_funding_rate_90d(funding_rates):
        """
        计算过去90天的平均年化资金费率
        :param funding_rates: 过去90天的资金费率列表
        :return: 平均年化资金费率
        """
        return sum(funding_rates) / len(funding_rates) if funding_rates else 0

    @staticmethod
    def calculate_median_ann_funding_rate_90d(funding_rates):
        """
        计算过去90天的中位数年化资金费率
        :param funding_rates: 过去90天的资金费率列表
        :return: 中位数年化资金费率
        """
        sorted_rates = sorted(funding_rates)
        n = len(sorted_rates)
        if n == 0:
            return 0
        mid = n // 2
        return (sorted_rates[mid] + sorted_rates[~mid]) / 2 if n % 2 == 0 else sorted_rates[mid]

    @staticmethod
    def calculate_std_dev_ann_funding_rate_90d(funding_rates):
        """
        计算过去90天的年化资金费率标准差
        :param funding_rates: 过去90天的资金费率列表
        :return: 年化资金费率标准差
        """
        if not funding_rates:
            return 0
        mean = sum(funding_rates) / len(funding_rates)
        variance = sum((x - mean) ** 2 for x in funding_rates) / len(funding_rates)
        return variance ** 0.5

    @staticmethod
    def calculate_positive_rate_pct_90d(funding_rates):
        """
        计算过去90天资金费率为正的百分比
        :param funding_rates: 过去90天的资金费率列表
        :return: 资金费率为正的百分比
        """
        if not funding_rates:
            return 0
        positive_count = sum(1 for rate in funding_rates if rate > 0)
        return (positive_count / len(funding_rates)) * 100

    @staticmethod
    def calculate_avg_basis_90d(basis_values):
        """
        计算过去90天的平均基差
        :param basis_values: 过去90天的基差列表
        :return: 平均基差
        """
        return sum(basis_values) / len(basis_values) if basis_values else 0

    @staticmethod
    def calculate_median_basis_90d(basis_values):
        """
        计算过去90天的中位数基差
        :param basis_values: 过去90天的基差列表
        :return: 中位数基差
        """
        sorted_basis = sorted(basis_values)
        n = len(sorted_basis)
        if n == 0:
            return 0
        mid = n // 2
        return (sorted_basis[mid] + sorted_basis[~mid]) / 2 if n % 2 == 0 else sorted_basis[mid]

    @staticmethod
    def calculate_std_dev_basis_90d(basis_values):
        """
        计算过去90天的基差标准差
        :param basis_values: 过去90天的基差列表
        :return: 基差标准差
        """
        if not basis_values:
            return 0
        mean = sum(basis_values) / len(basis_values)
        variance = sum((x - mean) ** 2 for x in basis_values) / len(basis_values)
        return variance ** 0.5

    @staticmethod
    def calculate_basis_funding_correlation_90d(basis_values, funding_rates):
        """
        计算过去90天基差与资金费率的相关系数
        :param basis_values: 过去90天的基差列表
        :param funding_rates: 过去90天的资金费率列表
        :return: 基差与资金费率的相关系数
        """
        if len(basis_values) != len(funding_rates) or not basis_values:
            return 0
        mean_basis = sum(basis_values) / len(basis_values)
        mean_funding = sum(funding_rates) / len(funding_rates)
        covariance = sum((basis_values[i] - mean_basis) * (funding_rates[i] - mean_funding) for i in range(len(basis_values))) / len(basis_values)
        std_dev_basis = StrategyHelper.calculate_std_dev_basis_90d(basis_values)
        std_dev_funding = StrategyHelper.calculate_std_dev_ann_funding_rate_90d(funding_rates)
        return covariance / (std_dev_basis * std_dev_funding) if std_dev_basis and std_dev_funding else 0

