#
# Created : 2018-02-09
#
# @author: Eric Lapouyade
#


class ListingException(Exception):
    pass


class InvalidListingConfiguration(ListingException):
    pass


class InvalidListing(ListingException):
    pass


class InvalidColumn(ListingException):
    pass


class InvalidQueryString(ListingException):
    pass


class InvalidHTMLAttribute(ListingException):
    pass


class InvalidData(ListingException):
    pass


class InvalidRecordKey(ListingException):
    pass


class InvalidToolbarItem(ListingException):
    pass


class InvalidFilters(ListingException):
    pass


class InvalidAggregation(ListingException):
    pass


class InvalidListingForm(ListingException):
    pass


class InvalidAttachedForm(ListingException):
    pass
