# Place Table

`national_place2020.txty` contains a single record for every place in the state/nation sorted by "STATEFP" and then "PLACEFP".  When the place extends into multiple counties, those counties are listed in the “COUNTIES” field.  In the example below the “Fanning springs city” extends into Gilchrist and Levy Counties. This is downloaded from the [ANSI and FIPS Codes](https://www.census.gov/library/reference/code-lists/ansi.html#place) page of the Census Bureau website. The direct file link is [here](https://www2.census.gov/geo/docs/reference/codes2020/national_place2020.txt).

| Field Name | Field Description                                         | Example                         |
|------------|-----------------------------------------------------------|---------------------------------|
| STATE      | State postal abbreviation                                 | FL                              |
| STATEFP    | State FIPS code                                           | 12                              |
| PLACEFP    | Place FIPS code                                           | 21850                           |
| PLACENS    | Place NS code                                             | 02403596                        |
| PLACENAME  | Place name and legal/statistical area description         | Fanning Springs city            |
| TYPE       | Place type                                                | Incorporated Place              |
| CLASSFP    | FIPS class code                                           | C1                              |
| FUNCSTAT   | Legal functional status                                   | A                               |
| COUNTIES   | Name of county or counties in which this place is located | Gilchrist County~~~ Levy County |

# State and State Equivalents

`national_state2020.txt` is used to look up state name from state abbreviation. This is downloaded from the [ANSI and FIPS Codes](https://www.census.gov/library/reference/code-lists/ansi.html#states) page of the Census Bureau website. The direct file link is [here](https://www2.census.gov/geo/docs/reference/codes2020/national_state2020.txt)

| Field Name | Field Description         | Example  |
|------------|---------------------------|----------|
| STATE      | State postal abbreviation | VA       |
| STATEFP    | State FIPS code           | 51       |
| STATENS    | State NS code             | 01779803 |
| STATE_NAME | State name                | Virginia |