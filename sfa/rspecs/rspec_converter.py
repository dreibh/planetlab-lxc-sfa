#!/usr/bin/python

from sfa.rspecs.pg_rspec_converter import PGRSpecConverter
from sfa.rspecs.sfa_rspec_converter import SfaRSpecConverter
from sfa.rspecs.sfa_rspec import sfa_rspec_version
from sfa.rspecs.pg_rspec import pg_rspec_ad_version, pg_rspec_request_version
from sfa.rspecs.rspec_parser import parse_rspec


class RSpecConverter:

    @staticmethod
    def to_sfa_rspec(in_rspec):
        rspec = parse_rspec(in_rspec)
        if rspec.version['type'] == sfa_rspec_version['type']: 
          return in_rspec
        elif rspec.version['type'] == pg_rspec_ad_version['type']:
            return PGRSpecConverter.to_sfa_rspec(in_rspec)
        else:
            return in_rspec 

    @staticmethod 
    def to_pg_rspec(in_rspec):
        rspec = parse_rspec(in_rspec)
        if rspec.version['type'] == pg_rspec_ad_version['type']:
            return in_rspec
        elif rspec.version['type'] == sfa_rspec_version['type']:
            return SfaRSpecConverter.to_pg_rspec(in_rspec)
        else:
            return in_rspec 


if __name__ == '__main__':
    pg_rspec = 'test/protogeni.rspec'
    sfa_rspec = 'test/nodes.rspec'  

    print "converting pg rspec to sfa rspec"
    print RSpecConverter.to_sfa_rspec(pg_rspec)
    
    print "converting sfa rspec to pg rspec"
    print RSpecConverter.to_pg_rspec(sfa_rspec)                   
