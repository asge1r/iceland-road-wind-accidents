"""Re-fit supporting estimates from unchanged canonical analysis inputs."""
from recompute import run

for module,args in [
 ('src.tables.rate',()),
 ('src.tables.temp_rate',()),
 ('src.tables.estimated_rate',()),
 ('src.tables.rate',('--outcome','serious-fatal','--output','reports/main/tables/wind_rate_severity.csv')),
 ('src.tables.rate',('--outcome','one','--coarse','--output','reports/main/tables/wind_rate_one.csv')),
 ('src.tables.rate',('--outcome','two-plus','--coarse','--output','reports/main/tables/wind_rate_multiple.csv')),
 ('src.tables.season_rate',()),
 ('src.tables.season_rate',('--outcome','serious-fatal','--output','reports/main/tables/season_rate_severity.csv')),
 ('src.tables.allocated_rate',()),
 ('src.tables.allocated_rate',('--outcome','serious-fatal','--output','reports/main/tables/allocated_rate_severity.csv','--audit','reports/working/tables/allocated_rate_severity_audit.csv')),
]:
 run(module,*args)
