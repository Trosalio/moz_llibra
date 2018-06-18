import datetime

from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views import generic
from django.urls import reverse_lazy, reverse

from .models import Author, Book, BookInstance
from .forms import RenewBookModelForm


def index(request):
    """
    View function for home page of site.
    """
    # Generate counts of some of the main objects
    num_books = Book.objects.all().count()

    # Number of visits to this view, as counted in the session variable.
    num_visits = request.session.get('num_visits', 0)
    request.session['num_visits'] = num_visits + 1

    num_instances = BookInstance.objects.all().count()
    # Available books (status = 'a')
    num_instances_available = BookInstance.objects.filter(status__exact='a').count()
    num_authors = Author.objects.count()  # The 'all()' is implied by default.

    # Render the HTML template index.html with the data in the context variable
    return render(
        request,
        'catalog/index.html',
        context={'num_books': num_books, 'num_instances': num_instances,
                 'num_instances_available': num_instances_available, 'num_authors': num_authors,
                 'num_visits': num_visits},  # num_visits appended
    )


class AuthorListView(generic.ListView):
    model = Author

    paginate_by = 10

    login_url = '/login/'
    redirect_field_name = 'redirect_to'


class AuthorDetailView(generic.DetailView):
    model = Author


class AuthorCreate(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    model = Author
    fields = '__all__'
    initial = {'date_of_death': '05/01/2018', }

    permission_required = 'catalog.add_author'


class AuthorUpdate(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    model = Author
    fields = ['first_name', 'last_name', 'date_of_birth', 'date_of_death']

    permission_required = 'catalog.change_author'


class AuthorDelete(LoginRequiredMixin, PermissionRequiredMixin, generic.DeleteView):
    model = Author
    success_url = reverse_lazy('authors')

    permission_required = 'catalog.delete_author'


class BookListView(generic.ListView):
    model = Book
    paginate_by = 1

    # def get_queryset(self):
    #     return Book.objects.filter(title__icontains='w')[:5]  # Get 5 books containing the title w

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super(BookListView, self).get_context_data(**kwargs)
        # Create any data and add it to the context
        context['some_data'] = 'This is just some data'
        return context


class BookDetailView(generic.DetailView):
    model = Book


class BookCreate(LoginRequiredMixin, PermissionRequiredMixin, generic.CreateView):
    model = Book
    fields = '__all__'

    permission_required = 'catalog.add_book'


class BookUpdate(LoginRequiredMixin, PermissionRequiredMixin, generic.UpdateView):
    model = Book
    field = '__all__'

    permission_required = 'catalog.change_book'


class BookDelete(LoginRequiredMixin, PermissionRequiredMixin, generic.DeleteView):
    model = Book
    success_url = reverse_lazy('books')

    permission_required = 'catalog.delete_book'


class LoanedBooksByUserListView(LoginRequiredMixin, generic.ListView):
    """
    Generic class-based view listing books on loan to current user.
    """
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_user.html'
    paginate_by = 10

    def get_queryset(self):
        return BookInstance.objects.filter(borrower=self.request.user).filter(status__exact='o').order_by('due_back')


class AllLoanedBooksListView(LoginRequiredMixin, PermissionRequiredMixin, generic.ListView):
    """
    Generic class-based view listing books on loan to current user.
    """
    model = BookInstance
    template_name = 'catalog/bookinstance_list_borrowed_all.html'
    paginate_by = 10
    permission_required = 'catalog.can_mark_returned'

    def get_queryset(self):
        return BookInstance.objects.filter(status__exact='o').order_by('due_back')


@login_required
@permission_required('catalog.can_renew_books')
def renew_book_librarian(request, pk):
    book_inst = get_object_or_404(BookInstance, pk=pk)

    # If this is a POST request then process the Form data
    if request.method == 'POST':

        # Create a form instance and populate it with data from the request (binding):
        form = RenewBookModelForm(request.POST)

        # Check if the form is valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required (here we just write it to the model due_back field)
            book_inst.due_back = form.cleaned_data['due_back']
            book_inst.save()

            # redirect to a new URL:
            return HttpResponseRedirect(reverse('all-borrowed'))

    # If this is a GET (or any other method) create the default form.
    else:
        proposed_renewal_date = datetime.date.today() + datetime.timedelta(weeks=3)
        form = RenewBookModelForm(initial={'due_back': proposed_renewal_date, })

    return render(request, 'catalog/book_renew_librarian.html', {'form': form, 'bookinst': book_inst})
