

from typing import Optional, Sequence
import abc
import codecs
import contextlib
#import csv
import datetime

from decimal import Decimal


from basana.core import pair, event, bar




class RowParser(metaclass=abc.ABCMeta):
    def __init__(
            self, pair: pair.Pair, tzinfo: datetime.tzinfo, timedelta: datetime.timedelta
    ):
        self.pair = pair
        self.tzinfo = tzinfo
        self.timedelta = timedelta

    def parse_row(self, row_dict: dict) -> Sequence[event.Event]:
        # File format:
        #
        # datetime,open,high,low,close,volume
        # 2015-01-01 00:00:00,321,321,321,321,1.73697242

        #print(row_dict)
        #volume =row_dict[5]
        # Skip bars with no volume.
        #if volume == 0:
            #return []

        #dt = datetime.datetime.strptime(row_dict[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=self.tzinfo)
        dt=datetime.datetime.fromtimestamp(row_dict[0]).replace(tzinfo=self.tzinfo)
        return [
            bar.BarEvent(
                dt,
                bar.Bar(
                    dt, self.pair, Decimal(row_dict[1]), Decimal(row_dict[2]), Decimal(row_dict[3]),Decimal(row_dict[4]), Decimal(row_dict[5])
                )
            )
        ]





def load_and_yield(csv_items, row_parser: RowParser, dict_reader_kwargs: dict = {}):

    # Load events.
    #with open_file_with_detected_encoding(csv_path) as f:
    #dict_reader = csv.DictReader(csv_items, **dict_reader_kwargs)
    for row in csv_items:
        for ev in row_parser.parse_row(row):
            yield ev


class EventSource(event.EventSource, event.Producer):
    def __init__(self, csv_items, row_parser: RowParser, sort: bool = True, dict_reader_kwargs: dict = {}):
        super().__init__(producer=self)
        self._csv_items = csv_items
        self._row_parser = row_parser
        self._sort = sort
        self._dict_reader_kwargs = dict_reader_kwargs
        self._row_it = None

    async def initialize(self):
        self._row_it = load_and_yield(self._csv_items, self._row_parser, self._dict_reader_kwargs)

    async def finalize(self):
        self._row_it = None

    def pop(self) -> Optional[event.Event]:
        ret = None
        try:
            if self._row_it:
                ret = next(self._row_it)
        except StopIteration:
            self._row_it = None
        return ret


class BarSource(EventSource):
    def __init__(
            self, pair,csv_items, 
            sort: bool = False, tzinfo: datetime.tzinfo = datetime.timezone.utc,
            dict_reader_kwargs: dict = {}
    ):
        # The datetime in the files are the beginning of the period but we need to generate the event at the period's
        # end.
        #timedelta = period_to_timedelta.get(period)
        timedelta: datetime.timedelta = datetime.timedelta(hours=24),
        #assert timedelta is not None, "Invalid period"
        self.row_parser = RowParser(pair, tzinfo=tzinfo, timedelta=timedelta)
        super().__init__(csv_items, self.row_parser, sort=sort, dict_reader_kwargs=dict_reader_kwargs)
