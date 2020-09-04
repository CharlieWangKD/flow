from django.core.paginator import Paginator


def pageinator_tool(itemlist, page):
    paginator = Paginator(itemlist, 10)
    try:
        page = int(page)
    except Exception as e:
        page = 1
    # print(page)

    num_pages = paginator.num_pages
    if page > num_pages:
        page = 1

    ticpages = paginator.page(page)

    if num_pages < 5:
        pages = range(1, num_pages + 1)
    elif page <= 3:
        pages = range(1, 6)
    elif num_pages - page <= 2:
        pages = range(num_pages - 4, num_pages + 1)
    else:
        pages = range(page - 2, page + 3)

    return ticpages, pages
