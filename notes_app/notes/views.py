from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import NoteForm


@login_required
def note_create(request):
    if request.method == 'POST':
        form = NoteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('notes:note_create')
    else:
        form = NoteForm()

    return render(request, 'notes/note_form.html', {'form': form})
