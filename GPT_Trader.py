import backtrader as bt
import datetime
import requests
import json
import time
import pandas as pd
import yfinance as yf
from backtrader.indicators import BollingerBands
from nltk.sentiment import SentimentIntensityAnalyzer

class GPT3BasedTradingStrategy(bt.Strategy):
    params = (('period', 20), ('buy_threshold', 0.05), ('sell_threshold', -0.05))

    def __init__(self):
        self.spy = self.datas[0]
        self.bb = BollingerBands(self.spy, period=self.params.period)
        self.sia = SentimentIntensityAnalyzer()

    def next(self):
        if len(self.spy) < 30:
            return

        # Extract features
        features = self.ExtractFeatures()

        # Construct the prompt
        prompt = (
            'Given the Bollinger Bands data, gravity modeling, technical analysis, and statistical analysis such as normal distribution, '
            'please analyze the following SPY closing prices for the last 30 days: {}. '
            'Also take into account the Bollinger Bands values (upper band, middle band, lower band): {}, {}, {}.'
        ).format(features, self.bb.top[0], self.bb.mid[0], self.bb.bot[0])

        # Get the interpretation using the GPT-3 API
        interpretation = self.GetInterpretation(prompt)

        # Make the decision
        if interpretation is not None:
            self.MakeDecision(interpretation)

    def ExtractFeatures(self):
        # Just use the close prices as features for this simple example.
        return [self.spy.close[-i] for i in range(30, 0, -1)]

    def GetInterpretation(self, prompt):
        # Define your logic to fetch interpretation from GPT-3 API here
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer sk-INSERT HERE',
        }

        data = {
            'model': 'gpt-3.5-turbo',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 3000,
            'temperature': 0.7
        }

        response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, data=json.dumps(data))
        time.sleep(data['max_tokens'] * 0.5 / 1000)  # Time delay of 0.5 seconds per token

        # Parse the response
        try:
            response_json = json.loads(response.text)
        except json.JSONDecodeError:
            print(f"Failed to decode API response: {response.text}")
            return None

        if 'choices' not in response_json:
            print(f"'choices' not found in API response: {response.text}")
            return None

        return response_json['choices'][0]['message']['content']

    def MakeDecision(self, interpretation):
        # Calculate sentiment score
        sentiment_score = self.sia.polarity_scores(interpretation)

        # Current holding position
        holdings = self.getposition(self.spy).size

        if sentiment_score['compound'] > self.params.buy_threshold and holdings <= 0:
            self.order_target_percent(self.spy, target=1.0)  # Go all in
        elif sentiment_score['compound'] < self.params.sell_threshold and holdings >= 0:
            self.order_target_percent(self.spy, target=-1.0)  # Short sell

# Fetch SPY data
spy_data = yf.download('SPY', '2023-01-01', '2023-06-01')

# Instantiate the cerebro engine
cerebro = bt.Cerebro()

# Add data feed to Cerebro
data = bt.feeds.PandasData(dataname=spy_data)
cerebro.adddata(data)

# Add strategy to Cerebro
cerebro.addstrategy(GPT3BasedTradingStrategy)

# Set our desired starting cash
cerebro.broker.setcash(1000.0)

# Set the commission - 0.1% ... divide by 100 to remove the %
cerebro.broker.setcommission(commission=0.001)

# Run over everything
cerebro.run()

# Plot the result
cerebro.plot(style='candlestick')
