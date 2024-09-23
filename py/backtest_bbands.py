

from decimal import Decimal
import asyncio
import datetime
import logging

from basana.backtesting import  lending #charts,
from basana.core.logs import StructuredMessage
#from basana.external.binance import csv
import basana as bs
import basana.backtesting.exchange as backtesting_exchange

import position_manager
import bbands
import kantu
import kt_data
import kt_chart


async def main():
    #logging.basicConfig(level=logging.INFO, format="[%(asctime)s %(levelname)s] %(message)s")

    event_dispatcher = bs.backtesting_dispatcher()
    pair = bs.Pair(kantu.data.pair1, kantu.data.pair2)
    position_amount = Decimal(kantu.data.position_amount)
    stop_loss_pct = Decimal(kantu.data.stop_loss_pct)

    # We'll be opening short positions so we need to set a lending strategy when initializing the exchange.
    lending_strategy = lending.MarginLoans(pair.quote_symbol, default_conditions=lending.MarginLoanConditions(
        interest_symbol=pair.quote_symbol, interest_percentage=Decimal("7"),
        interest_period=datetime.timedelta(days=365), min_interest=Decimal("0.01"),
        margin_requirement=Decimal("0.5")
    ))
    exchange = backtesting_exchange.Exchange(
        event_dispatcher,
        initial_balances={pair.quote_symbol: Decimal(1200)},
        lending_strategy=lending_strategy,
    )
    exchange.set_symbol_precision(pair.base_symbol, 8)
    exchange.set_symbol_precision(pair.quote_symbol, 2)
    exchange.add_bar_source(kt_data.BarSource(pair,kantu.data.Load()))

    # Connect the strategy to the bar events from the exchange.
    strategy = bbands.Strategy(event_dispatcher, period=30, std_dev=2)
    exchange.subscribe_to_bar_events(pair, strategy.on_bar_event)

    # Connect the position manager to the strategy signals and to bar events.
    position_mgr = position_manager.PositionManager(
        exchange, position_amount, pair.quote_symbol, stop_loss_pct
    )
    strategy.subscribe_to_trading_signals(position_mgr.on_trading_signal)
    exchange.subscribe_to_bar_events(pair, position_mgr.on_bar_event)

    # Setup chart.
    chart = kt_chart.LineCharts(exchange)
    chart.add_pair(pair)
    chart.add_pair_indicator(        "Upper", pair, lambda _: strategy.bb[-1].ub if len(strategy.bb) and strategy.bb[-1] else None    )
    chart.add_pair_indicator(        "Central", pair, lambda _: strategy.bb[-1].cb if len(strategy.bb) and strategy.bb[-1] else None    )
    chart.add_pair_indicator(        "Lower", pair, lambda _: strategy.bb[-1].lb if len(strategy.bb) and strategy.bb[-1] else None    )
    chart.add_balance(pair.base_symbol)
    chart.add_balance(pair.quote_symbol)
    chart.add_portfolio_value(pair.quote_symbol)

    # Run the backtest.
    await event_dispatcher.run()

    # Log balances.
    balances = await exchange.get_balances()
    for currency, balance in balances.items():
        logging.info(StructuredMessage(f"{currency} balance", available=balance.available))

    #chart.show()
   

    kantu.data.Show("portfolio",chart._portfolio_charts['USDT']._ts._values);



if __name__ == "__main__":
    asyncio.run(main())
