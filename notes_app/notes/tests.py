from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .forms import NoteForm
from .models import Note


class NoteModelTests(TestCase):
    def test_created_at_is_populated_when_note_is_saved(self):
        note = Note.objects.create(
            title='Grocery list',
            text_body='Buy milk and eggs.',
        )

        self.assertIsNotNone(note.created_at)
        self.assertEqual(str(note), note.title)


class NoteCreateViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tester',
            password='testpass123',
        )
        self.client.force_login(self.user)

    def test_anonymous_get_is_redirected_to_login(self):
        self.client.logout()
        response = self.client.get(reverse('notes:note_create'))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Note.objects.count(), 0)

    def test_anonymous_post_cannot_create_note(self):
        self.client.logout()
        response = self.client.post(
            reverse('notes:note_create'),
            {'title': 'Spam', 'text_body': 'Should not be created.'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Note.objects.count(), 0)

    def test_get_renders_note_form(self):
        response = self.client.get(reverse('notes:note_create'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'notes/note_form.html')
        self.assertIsInstance(response.context['form'], NoteForm)

    def test_valid_post_creates_note_and_redirects(self):
        response = self.client.post(
            reverse('notes:note_create'),
            {'title': 'Meeting notes', 'text_body': 'Discuss budget.'},
        )

        self.assertRedirects(response, reverse('notes:note_create'))
        self.assertEqual(Note.objects.count(), 1)
        note = Note.objects.get()
        self.assertEqual(note.title, 'Meeting notes')
        self.assertEqual(note.text_body, 'Discuss budget.')

    def test_invalid_post_does_not_create_note(self):
        response = self.client.post(
            reverse('notes:note_create'),
            {'title': '', 'text_body': ''},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Note.objects.count(), 0)
