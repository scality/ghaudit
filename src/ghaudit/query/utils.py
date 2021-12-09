def page_info_continue(page_infos):
    if not page_infos or page_infos["hasNextPage"]:
        return True
    return False
