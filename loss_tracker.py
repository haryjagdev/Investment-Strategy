import pandas as pd
import numpy as np
import datetime

def read_price_data():
    # read stock price data to memory 
    filename = 'data/price data for all companies.csv'
    df = pd.read_csv(filename)
    df.date = pd.to_datetime(df.date, errors='coerce', utc=True).dt.date
    df.set_index('date', inplace=True)
    return df

def read_news_data():
    # read news data into memory
    filename = 'data/news headlines.csv'
    df = pd.read_csv(filename, usecols=[1,2,3])
    df.date = pd.to_datetime(df.date, errors='coerce', utc=True).dt.date
    return df

def calculate_r(symbol, investment_date, r_df, holding_period):
    '''
    Calculate return based on holding period (days)
    '''
    if pd.isnull(investment_date):
        return None
    
    # remove empty dates
    # market closed based on local holiday, which is different for some countries
    r_df = r_df.loc[:, [symbol]]
    r_df.dropna(inplace=True)
    
    # reset_index to get position of investment date and add holding period
    index = r_df.reset_index()[r_df.reset_index().date == investment_date].index[0]
    
    # return none if holdingPeriod from investment date exceeds data set
    if (index + holding_period) >= len(r_df):
        return None

    daily_r = r_df.iloc[index+1:index+holding_period+1, r_df.columns==symbol]
    period_r = np.product(1 + daily_r.values) - 1
    return period_r

def calc_r_for_series(s, r_df, holding_period):
    '''
    Calculate return for Series of dates
    '''
    symbol = s.name
    result = s.apply(lambda x: calculate_r(symbol, x, r_df, holding_period))
    return result

def get_news_headlines(df_news, date, symbol, days_aparts=1):
    '''
    return {date: headline}
    '''
    if type(date) != datetime.date:
        return None
    dates = [date]
    for i in range(1, days_aparts + 1):
        dates.append(date + datetime.timedelta(days=i))
        dates.append(date - datetime.timedelta(days=i))
    # print(dates)
    mask = (df_news.date.isin(dates)) & (df_news.stock == symbol)
    df = df_news[mask]
    headlines = dict(zip(df.date.apply(lambda x: str(x)).values, df.title.values))
    return headlines

def get_news_list(df_news, s_dates, days_aparts=1):
    '''
    return dataframe with a list of headlines for date +- days_aparts
    
    '''
    return s_dates.apply(lambda x: get_news_headlines(df_news, x, s_dates.name, days_aparts=days_aparts))
    

class StockData():
    def __init__(self):
        self.price = read_price_data()
        self.returnData = "NO VALUE -> run calc_r"
        self.targetDecrease = "No VALUE -> run calc_dates_below_target"
        self.datesBelowTarget = "NO VALUE -> run calc_dates_below_target"
        self.newsData = "NO VALUE -> run source_news_data"
    
    def calc_dates_return(self, target_loss, holding_period):
        self.calc_dates_below_target(target=target_loss)
        self.calc_r_for_dates_below_target(holding_period=holding_period)

    def source_news_data(self):
        print("Souring news data...")
        self.newsData = read_news_data()

    def calc_r(self, days=1):
        self.returnData = self.price / self.price.shift(1) - 1
        self.returnData.index.name = f"{days}d_r"

    def calc_dates_below_target(self, target):
        '''
        calculate dates where daily return is less than target 
        '''
        df_date = self.price.apply(lambda x: x.index)
        df_r = self.price / self.price.shift(1) - 1
        datesBelowTarget = df_date[df_r <= target]
        datesBelowTarget.reset_index(drop=True, inplace=True)
        # move values up by removing nan from each Series and combining to DataFrame
        datesBelowTarget = datesBelowTarget.apply(lambda x: pd.Series(x.dropna(axis=0).values), axis=0)
        datesBelowTarget.dropna(axis=1, thresh=1, inplace=True)

        self.targetDecrease = target
        self.datesBelowTarget = datesBelowTarget

    def calc_r_for_dates_below_target(self, holding_period=100):
        dfR = self.price / self.price.shift(1) - 1
        _ = self.datesBelowTarget.apply(lambda x: calc_r_for_series(x, dfR, holding_period=holding_period))
        self.investmentReturn = _ 

    def source_news_for_dates(self, days_aparts=1, removeNull=True):
        _ = self.datesBelowTarget.apply(lambda x: get_news_list(self.newsData, x, days_aparts=days_aparts)) 
        if removeNull:
            _ = _.applymap(lambda x: None if x == {} else x)
            _.dropna(axis=1, how='all', inplace=True)
        self.newsByDate = _

    #  Getter methods
    def get_price_data(self):
        return self.price			
    
    def get_return_data(self):
        return self.returnData
    
    def get_target_decrease(self):
        return f"{self.targetDecrease * 100 : .2f}%"

    def get_dates_below_target(self):
        return self.datesBelowTarget
    
    def get_news_data(self):
        return self.newsData()

    def get_investment_return(self, to_array=False):
        if not to_array:
            return self.investmentReturn
        else:
            r = self.investmentReturn.values.reshape(-1)
            r = r[~np.isnan(r)]
            r = r[~np.isinf(r)]
            return r

    

if __name__ == '__main__':
    print("WORKING...")
    data = StockData()
    data.source_news_data()
    data.calc_dates_below_target(-0.4)
    data.source_news_for_dates(1)
    print(data.newsByDate)
