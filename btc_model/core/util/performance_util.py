import numpy as np
import pandas as pd
import datetime

class PerformanceUtil(object):

    def __init__(self, data: pd.DataFrame, simple_interest: bool = False):
        """
        @param data: DataFrame, columns[0] should be date, columns[1] should be value
        @param simple_interest: 单利 or 复利
        """
        self.compound_drawback = None
        self.simple_drawback = None
        self.returns = None

        self.date = data.iloc[:, 0].values
        self.simple_interest = simple_interest

        if self.simple_interest:
            self.simple_value = data.iloc[:, 1].values
            self._simple_to_compound()
        else:
            self.compound_value = data.iloc[:, 1].values
            self._compound_to_simple()

        self._internal_calculate_drawdown(choice_simple_interest=True)
        self._internal_calculate_drawdown(choice_simple_interest=False)

    def _calculate_returns(self):
        if self.simple_interest:
            self.returns = np.diff(self.simple_value)
        else:
            self.returns = np.diff(self.compound_value) / self.compound_value[0:len(self.compound_value) - 1]

    def _compound_to_simple(self):
        self._calculate_returns()
        self.simple_value = np.cumsum(np.insert(self.returns, 0, 1))

    def _simple_to_compound(self):
        self._calculate_returns()
        self.compound_value = np.cumprod(np.insert(self.returns + 1, 0, 1))

    def start_day(self):
        start_day = min(self.date) + datetime.timedelta(days=1)
        return start_day

    def end_day(self):
        return max(self.date)

    def select_return(self, date1, date2):
        if date1 < self.start_day():
            raise Exception('Please input a date after or equal to' + self.start_day())

        if date2 > self.end_day():
            raise Exception('Please input a date before or equal to' + self.end_day())

        date_index = (self.date >= date1) & (self.date <= date2)
        return_index = date_index[1:len(date_index)]

        return self.returns[return_index]

    def select_simple_value(self, date1, date2):
        if date1 < min(self.date):
            raise Exception('Please input a date after or equal to' + str(min(self.date)))

        if date2 > max(self.date):
            raise Exception('Please input a date before or equal to' + str(max(self.date)))

        date_index = (self.date >= date1) & (self.date <= date2)
        return self.simple_value[date_index]

    def select_compound_value(self, date1, date2):
        if date1 < min(self.date):
            raise Exception('Please input a date after or equal to' + min(self.date))

        if date2 > max(self.date):
            raise Exception('Please input a date before or equal to' + max(self.date))

        date_index = (self.date >= date1) & (self.date <= date2)

        return self.compound_value[date_index]

    def select_date(self, date1, date2):
        if date1 < min(self.date):
            raise Exception('Please input a date after or equal to' + min(self.date))

        if date2 > max(self.date):
            raise Exception('Please input a date before or equal to' + max(self.date))

        date_index = (self.date >= date1) & (self.date <= date2)

        return self.date[date_index]



    def return_by_day(self):
        ''' 得到每日收益以及累积收益 '''
        date_return = pd.DataFrame([self.date[1:], self.returns]).transpose()
        date_return.columns = ['date', 'return']
        temp = date_return['return'].values
        acc = np.add.accumulate(temp)
        date_return.loc[:, 'acc_return'] = acc
        return date_return





    def drawdown_single_point(self, pos, choice_simple_interest):
        if choice_simple_interest:
            value_prior = self.simple_value[:pos + 1]
            drawdown_single_point = np.max(value_prior) - self.simple_value[pos]
        else:
            value_prior = self.compound_value[:pos + 1]
            drawdown_single_point = (np.max(value_prior) - self.compound_value[pos]) / np.max(value_prior)
        return drawdown_single_point

    def _internal_calculate_drawdown(self, choice_simple_interest):
        if choice_simple_interest:
            self.simple_drawback = []
            for i in range(len(self.date)):
                drawdown_single_point = self.drawdown_single_point(i, choice_simple_interest=True)
                self.simple_drawback.append(drawdown_single_point)

        if not choice_simple_interest:
            self.compound_drawback = []
            for i in range(len(self.date)):
                drawdown_single_point = self.drawdown_single_point(i, choice_simple_interest=False)
                self.compound_drawback.append(drawdown_single_point)

    def simple_drawback_by_year(self):
        date_simple_drawback = pd.DataFrame([self.date, self.simple_drawback]).transpose()
        date_simple_drawback.columns = ['trade_date', 'simple_drawback']
        try:
            date_simple_drawback['simple_drawback'] = date_simple_drawback['simple_drawback'].apply(lambda x: x.item())
        except:
            print('No need to apply the operation from numpy.float64 to float64!\n')

        date_simple_drawback['year'] = date_simple_drawback['trade_date'].apply(lambda x: str(pd.to_datetime(x).year))
        group_by_year = date_simple_drawback.groupby(date_simple_drawback['year'])
        try:
            yearly_simple_drawback = group_by_year.agg({'simple_drawback': np.max})
        except:
            every_year_max = []
            for name, group in group_by_year:
                every_year_max.append(np.max(group['simple_drawback']))

            yearly_simple_drawback = pd.DataFrame(every_year_max)
            yearly_simple_drawback = yearly_simple_drawback.set_index(date_simple_drawback['year'].unique())

        return yearly_simple_drawback

    def compound_drawback_by_year(self):
        date_simple_drawback = pd.DataFrame([self.date, self.compound_drawback]).transpose()
        date_simple_drawback.columns = ['trade_date', 'simple_drawback']
        date_simple_drawback['simple_drawback'] = date_simple_drawback['simple_drawback'].apply(lambda x: x.item())
        date_simple_drawback['year'] = date_simple_drawback['trade_date'].apply(lambda x: str(pd.to_datetime(x).year))
        group_by_year = date_simple_drawback.groupby(date_simple_drawback['year'])
        try:
            yearly_simple_drawback = group_by_year.agg({'simple_drawback': np.max})
        except:
            every_year_max = []
            for name, group in group_by_year:
                every_year_max.append(np.max(group['simple_drawback']))

            yearly_simple_drawback = pd.DataFrame(every_year_max)
            yearly_simple_drawback = yearly_simple_drawback.set_index(date_simple_drawback['year'].unique())

        return yearly_simple_drawback

    def yearly_sharpe_ratio_duration(self, timestamp1, timestamp2):
        returns = self.select_return(timestamp1, timestamp2)
        avg_return = np.mean(returns) * np.sqrt(252)
        std_return = np.std(returns)
        return avg_return / std_return

    #-----------------------------------------------------------------------------------------------------------------
    def yearly_profit(self, choice_simple_interest: bool = False):
        """
        计算年化收益率
        @return: 年化收益率
        """
        if choice_simple_interest:
            val = self.simple_value
        else:
            val = self.compound_value

        ret = (val[-1] / val[0]) ** (250 / (len(val) - 1)) - 1
        return ret

    def max_drawdown(self, choice_simple_interest: bool = False):
        if choice_simple_interest:
            return np.max(self.simple_drawback)
        else:
            return np.max(self.compound_drawback)

    def yearly_sharpe_ratio(self):
        avg_return = np.mean(self.returns) * np.sqrt(250)
        std_return = np.std(self.returns)
        return avg_return / std_return

    def yearly_volatility(self):
        volatility = np.std(self.returns) * np.sqrt(250)
        return volatility
    # -----------------------------------------------------------------------------------------------------------------

    def win_rate(self):
        """
        计算胜率
        @return:
        """

        return sum(self.returns > 0) / sum(self.returns != 0)

    def profit_and_loss_ratio(self, weighted_ratio=False):
        """
        计算盈亏比
        @param weighted_ratio: True 考虑盈利和亏损的波动性
        @return:
        """
        avg_profit = np.mean(self.returns[self.returns > 0])
        avg_loss = np.mean(self.returns[self.returns < 0])

        if not weighted_ratio:
            return np.abs(avg_profit / avg_loss)
        else:
            # 计算盈利和亏损的标准差
            std_profit = np.std(self.returns[self.returns > 0])
            std_loss = np.std(self.returns[self.returns < 0])

            # 计算加权盈亏比，考虑盈利和亏损的波动性
            weighted_ratio = np.abs(avg_profit / avg_loss) * (std_loss / std_profit)

            return weighted_ratio

    # -----------------------------------------------------------------------------------------------------------------
    def return_by_year(self):
        """
        计算逐年的回报
        @return:
        """
        date_return = pd.DataFrame([self.date[1:], self.returns]).transpose()
        date_return.columns = ['date', 'return']
        date_return['return'] = date_return['return'].apply(lambda x: x.item())
        date_return['year'] = date_return['date'].apply(lambda x: str(pd.to_datetime(x).year))

        group_by_year = date_return.groupby(date_return['year'])

        try:
            yearly_sum = group_by_year.agg({'return': np.sum})
        except:
            every_year_sum = []
            for name, group in group_by_year:
                every_year_sum.append(np.sum(group['return']))

            yearly_sum = pd.DataFrame(every_year_sum)
            yearly_sum.columns = ['return']
            yearly_sum = yearly_sum.set_index(date_return['year'].unique())

        return yearly_sum

    def return_by_month(self):
        """
        计算逐月的回报（优化版）
        @return: 包含年月和对应累计收益的DataFrame
        """
        # 创建包含日期和收益的DataFrame
        date_return = pd.DataFrame({
            'date': self.date[1:],
            'return': self.returns
        })
        
        # 将日期转换为datetime类型
        date_return['date'] = pd.to_datetime(date_return['date'])
        
        # 提取年月信息（格式为"YYYY-MM"）
        date_return['year_month'] = date_return['date'].dt.strftime('%Y-%m')
        
        # 按年月分组并计算累计收益
        monthly_sum = date_return.groupby('year_month')['return'].sum().reset_index()
        monthly_sum.columns = ['year_month', 'monthly_return']
        
        return monthly_sum
    
    

    def sharpe_ratio_by_year(self):
        """
        计算逐年的夏普比率
        @return:
        """
        date_return = pd.DataFrame([self.date[1:], self.returns]).transpose()
        date_return.columns = ['trade_date', 'return']
        try:
            date_return['return'] = date_return['return'].apply(lambda x: x.item())
        except:
            print('No need to apply the operation from numpy.float64 to float64!\n')

        date_return['year'] = date_return['trade_date'].apply(lambda x: str(pd.to_datetime(x).year))
        group_by_year = date_return.groupby(date_return['year'])
        try:
            yearly_mean_std = group_by_year.agg({'return': [np.mean, np.std]})
        except:
            every_year_mean = []
            every_year_std = []
            for name, group in group_by_year:
                every_year_mean.append(np.mean(group['return']))
                every_year_std.append(np.std(group['return']))

            yearly_mean_std = pd.DataFrame([every_year_mean, every_year_std]).transpose()
            yearly_mean_std = yearly_mean_std.set_index(date_return['year'].unique())

        sharpe_ratio_yearly = yearly_mean_std.iloc[:, 0] * np.sqrt(252) / yearly_mean_std.iloc[:, 1]
        return [
            yearly_mean_std, sharpe_ratio_yearly]


    def sharpe_ratio_by_month(self):
        """
        计算逐月的夏普比率
        @return:
        """
        date_return = pd.DataFrame([self.date[1:], self.returns]).transpose()
        date_return.columns = ['trade_date', 'return']
        try:
            date_return['return'] = date_return['return'].apply(lambda x: x.item())
        except:
            print('No need to apply the operation from numpy.float64 to float64!\n')

        date_return['month'] = date_return['trade_date'].apply(lambda x: str(pd.to_datetime(x).month))
        group_by_month = date_return.groupby(date_return['month'])
        try:
            monthly_mean_std = group_by_month.agg({'return': [np.mean, np.std]})
        except:
            every_month_mean = []
            every_month_std = []
            for name, group in group_by_month:
                every_month_mean.append(np.mean(group['return']))
                every_month_std.append(np.std(group['return']))

            monthly_mean_std = pd.DataFrame([every_month_mean, every_month_std]).transpose()
            monthly_mean_std = monthly_mean_std.set_index(date_return['month'].unique())

        sharpe_ratio_monthly = monthly_mean_std.iloc[:, 0] * np.sqrt(252) / monthly_mean_std.iloc[:, 1]
        return [monthly_mean_std, sharpe_ratio_monthly]

