def pre_paginate(get_big_qs):
    def pre_filterer(self, *args, **kwargs):
        qs = get_big_qs(self, *args, **kwargs)
        pg_filter = {}
        offset = self.get_offset_object(qs)
        
        if offset:
            last = len(self.paginate_kwargs) - 1
            for i, kw in enumerate(self.paginate_kwargs):
                if kw.startswith('-'):
                    kw = kw[1:]
                    pg_filter[f'{kw}{"__lt" if i==last else "__lte"}'] = self._get_attr(offset, kw)
                else:
                    pg_filter[f'{kw}{"__gt" if i==last else "__gte"}'] = self._get_attr(offset, kw)

        qs = qs.filter(**pg_filter)
        qs = qs.order_by(*self.paginate_kwargs)
        return qs
    return pre_filterer

def slice_big_qs(get_filtered):
    def slicer(self, *args, **kwargs):
        qs = get_filtered(self, *args, **kwargs)
        limit_qp = self.request.query_params.get("limit", '')
        return qs[:int(limit_qp) if limit_qp.isdigit() else self.paginate_limit]
    return slicer


class PaginationMixin(object):
    paginate_kwargs = ('-id',)
    paginate_limit = 10
    offset_prop = 'pk'

    def get_offset_object(self, qs):
        obj_id = self.request.query_params.get("offset", None)
        if obj_id:
            try: return qs.get(**{self.offset_prop: obj_id})
            except: pass
        return None

    def _get_attr(self, *args):
        offset = args[0]
        if hasattr(offset, args[1]):
            return getattr(offset, args[1])
        attr_list = args[1].split('__')
        for attr in attr_list:
            # for reverse FK or M2M, use anotate
            offset = getattr(offset, attr)
        return offset

    def get_big_queryset(self):
        return self.queryset

    @slice_big_qs
    @pre_paginate
    def get_queryset(self):
        return self.get_big_queryset()


class SrchCompatiblePgnationMixin(PaginationMixin):
    @pre_paginate
    def get_pre_searched_qs(self):
        return self.get_big_queryset()

    @slice_big_qs
    def filter_queryset(self, queryset, *args, **kwargs): # DRF filter backend
        return super().filter_queryset(queryset = self.get_pre_searched_qs(), *args, **kwargs)
