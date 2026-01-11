"""
Monthly Filter Utilities
Reusable functions for implementing monthly filtering across different sections
"""

import calendar
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone


def get_available_years(model, date_field="created_at"):
    """
    Get available years from a model's date field

    Args:
        model: Django model class
        date_field: Name of the date field to extract years from

    Returns:
        List of years in descending order
    """
    try:
        years = model.objects.dates(date_field, "year", order="DESC")
        return [year.year for year in years]
    except Exception:
        current_year = timezone.now().year
        return list(range(current_year, current_year - 5, -1))


def apply_monthly_filter(queryset, request, date_field="created_at"):
    """
    Apply monthly filtering to a queryset based on request parameters

    Args:
        queryset: Django QuerySet to filter
        request: HTTP request object
        date_field: Name of the date field to filter on

    Returns:
        Filtered queryset and filter context
    """
    year = request.GET.get("year", "")
    month = request.GET.get("month", "")

    filter_context = {
        "selected_year": year,
        "selected_month": month,
        "has_monthly_filter": bool(year or month),
    }

    # Apply year filter
    if year:
        try:
            year_int = int(year)
            year_filter = {f"{date_field}__year": year_int}
            queryset = queryset.filter(**year_filter)
            filter_context["year_applied"] = year_int
        except (ValueError, TypeError):
            pass

    # Apply month filter
    if month:
        try:
            month_int = int(month)
            if 1 <= month_int <= 12:
                month_filter = {f"{date_field}__month": month_int}
                queryset = queryset.filter(**month_filter)
                filter_context["month_applied"] = month_int
                filter_context["month_name"] = get_month_name(month_int)
        except (ValueError, TypeError):
            pass

    return queryset, filter_context


def get_month_name(month_number):
    """
    Get Arabic month name from month number

    Args:
        month_number: Integer month number (1-12)

    Returns:
        Arabic month name
    """
    months = {
        1: "يناير",
        2: "فبراير",
        3: "مارس",
        4: "أبريل",
        5: "مايو",
        6: "يونيو",
        7: "يوليو",
        8: "أغسطس",
        9: "سبتمبر",
        10: "أكتوبر",
        11: "نوفمبر",
        12: "ديسمبر",
    }
    return months.get(int(month_number), str(month_number))


def get_monthly_analytics(queryset, date_field="created_at", year=None):
    """
    Get monthly analytics for a queryset

    Args:
        queryset: Django QuerySet to analyze
        date_field: Name of the date field to analyze
        year: Specific year to analyze (defaults to current year)

    Returns:
        Dictionary with monthly analytics data
    """
    if year is None:
        year = timezone.now().year

    # Filter by year
    year_filter = {f"{date_field}__year": year}
    yearly_queryset = queryset.filter(**year_filter)

    # Get monthly counts
    monthly_data = []
    for month in range(1, 13):
        month_filter = {f"{date_field}__month": month}
        month_count = yearly_queryset.filter(**month_filter).count()
        monthly_data.append(
            {"month": month, "month_name": get_month_name(month), "count": month_count}
        )

    # Calculate totals and averages
    total_count = yearly_queryset.count()
    avg_per_month = total_count / 12 if total_count > 0 else 0

    # Find peak month
    peak_month = max(monthly_data, key=lambda x: x["count"]) if monthly_data else None

    return {
        "year": year,
        "monthly_data": monthly_data,
        "total_count": total_count,
        "avg_per_month": round(avg_per_month, 2),
        "peak_month": peak_month,
    }


def get_date_range_for_month(year, month):
    """
    Get start and end dates for a specific month

    Args:
        year: Year as integer
        month: Month as integer (1-12)

    Returns:
        Tuple of (start_date, end_date)
    """
    try:
        start_date = datetime(year, month, 1)

        # Get last day of month
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)

        return start_date, end_date
    except (ValueError, TypeError):
        return None, None


def get_quarter_months(quarter):
    """
    Get months for a specific quarter

    Args:
        quarter: Quarter number (1-4)

    Returns:
        List of month numbers
    """
    quarters = {
        1: [1, 2, 3],  # Q1: Jan, Feb, Mar
        2: [4, 5, 6],  # Q2: Apr, May, Jun
        3: [7, 8, 9],  # Q3: Jul, Aug, Sep
        4: [10, 11, 12],  # Q4: Oct, Nov, Dec
    }
    return quarters.get(quarter, [])


def apply_quarter_filter(queryset, quarter, year=None, date_field="created_at"):
    """
    Apply quarter filtering to a queryset

    Args:
        queryset: Django QuerySet to filter
        quarter: Quarter number (1-4)
        year: Year (defaults to current year)
        date_field: Name of the date field to filter on

    Returns:
        Filtered queryset
    """
    if year is None:
        year = timezone.now().year

    months = get_quarter_months(quarter)
    if not months:
        return queryset

    # Create Q objects for each month in the quarter
    month_filters = Q()
    for month in months:
        month_filter = Q(**{f"{date_field}__year": year, f"{date_field}__month": month})
        month_filters |= month_filter

    return queryset.filter(month_filters)


def get_monthly_comparison(queryset, date_field="created_at", months_back=3):
    """
    Get monthly comparison data for the last N months

    Args:
        queryset: Django QuerySet to analyze
        date_field: Name of the date field to analyze
        months_back: Number of months to go back

    Returns:
        List of monthly comparison data
    """
    now = timezone.now()
    comparison_data = []

    for i in range(months_back):
        # Calculate the month and year
        target_date = now - timedelta(days=30 * i)
        year = target_date.year
        month = target_date.month

        # Filter queryset for this month
        month_filter = {f"{date_field}__year": year, f"{date_field}__month": month}
        month_count = queryset.filter(**month_filter).count()

        comparison_data.append(
            {
                "year": year,
                "month": month,
                "month_name": get_month_name(month),
                "count": month_count,
                "date": target_date,
            }
        )

    return comparison_data


def format_filter_summary(year=None, month=None):
    """
    Format a human-readable filter summary

    Args:
        year: Selected year
        month: Selected month

    Returns:
        Formatted filter summary string
    """
    if year and month:
        month_name = get_month_name(int(month))
        return f"{month_name} {year}"
    elif year:
        return f"سنة {year}"
    elif month:
        month_name = get_month_name(int(month))
        return f"شهر {month_name}"
    else:
        return "جميع الفترات"
