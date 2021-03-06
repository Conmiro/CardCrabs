from django.core.exceptions import ObjectDoesNotExist
import json
from django.http import HttpResponse
from django.shortcuts import render
from .forms import AddSellerForm, AddCardDetailsForm, AddCardForm, ShippingInformationForm, BillingInformationForm, \
    RegisterForm
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from .models import *


def index(request):

    return render(request, 'index.html')


def my_store(request):

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'remove' or action == 'set':
            card_id = request.POST.get('card_id')
            card = Card.objects.get(pk=card_id)
        if action == 'remove':

            card.delete()
            return HttpResponse("Deleted!")

        if action == 'set':
            set_quantity = int(request.POST.get('quantity'))
            card.quantity = set_quantity
            card.save()
            return HttpResponse("Set!")


    user = request.user

    if str(user) != 'AnonymousUser':
        store = Store.objects.get(owner=user)
        context = {'store': store}
    else:
        context = { }



    return render(request, 'seller/my_store.html', context)

def my_store_body(request):
    user = request.user
    store = Store.objects.get(owner=user)

    cards = Card.objects.filter(store=store)

    context = {'cardlist': cards}
    return render(request, 'seller/my_store_body.html', context)

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        errors = []
        if form.is_valid():
            data = form.cleaned_data
            username = data['username']
            first_name = data['first_name']
            last_name = data['last_name']
            email = data['email']
            password = data['password']
            confirm_password = data['confirm_password']

            if User.objects.filter(username=username).exists():
                errors.append('USER_EXISTS')
            if password != confirm_password:
                errors.append('PASSWORD_MISMATCH')

            if errors:
                return HttpResponse(json.dumps(errors))
            else:
                user = User.objects.create_user(username, email, password)
                user.first_name = first_name
                user.last_name = last_name
                user.save()
                store = Store(owner=user, display_name=user.first_name)
                store.save()
                return HttpResponse("SUCCESS")


    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})


def shipping_billing_body(request):
    shipping_info = get_shipping(request)
    billing_info = get_billing(request)

    if request.method == 'POST':
        info_type = request.POST.get('info_type')
        if info_type=='billing':
            form = BillingInformationForm(request.POST, instance=billing_info)
            form.save()
        else:
            form = ShippingInformationForm(request.POST, instance=shipping_info)
            form.save()

        return render(request, 'checkout.html') # refresh checkout

    shipping_form = ShippingInformationForm(instance=shipping_info)
    billing_form = BillingInformationForm(instance=billing_info)


    context = {'shipping_info': shipping_info, 'billing_info': billing_info, 'shipping_form': shipping_form, 'billing_form': billing_form}
    return render(request, 'shipping_billing_body.html', context)


def cart_body(request):

    cart = get_cart(request)

    cardlist = cart.card_list.all()

    total = 0
    for cardincart in cart.cardincart_set.all():
        total += cardincart.card.price * cardincart.quantity

    for card in cardlist:
        cardincart = CardInCart.objects.get(cart=cart,card=card)
        card.total = cardincart.quantity * card.price
        card.quantity = cardincart.quantity

    context = {'cardlist': cardlist, 'total': total}

    return render(request, 'cart_body.html', context)





def checkout(request):

    return render(request, 'checkout.html')


# this is technically a "body"
def shopping_cart(request):

    cart = get_cart(request)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'clear':
            cart.card_list.clear()
            return HttpResponse("Cleared")

        card_id = request.POST.get('card_id')
        card = Card.objects.get(pk=card_id)

        if action == 'set':
            set_quantity = int(request.POST.get('quantity'))
            available_quantity = card.quantity
            card_in_cart = CardInCart.objects.get(cart=cart, card=card)

            if set_quantity > available_quantity:
                card_in_cart.quantity = available_quantity
                card_in_cart.save()
                return HttpResponse("Not Enough")

            card_in_cart.quantity = set_quantity
            card_in_cart.save()
            return HttpResponse("Set!")

        if action == 'remove':
            card_in_cart = CardInCart.objects.get(cart=cart, card=card)
            card_in_cart.delete()
            return HttpResponse("Removed!")

        add_quantity = int(request.POST.get('quantity'))
        available_quantity = card.quantity
        try:
            card_in_cart = CardInCart.objects.get(cart=cart, card=card)
            curr_quantity = card_in_cart.quantity

            new_quantity = add_quantity + curr_quantity
            if new_quantity > available_quantity:
                return HttpResponse("Not Enough")
            else:
                card_in_cart.quantity = new_quantity
                card_in_cart.save()

        except ObjectDoesNotExist:
            if add_quantity > available_quantity:
                return HttpResponse("Not Enough")
            else:
                CardInCart.objects.create(cart=cart, card=card, quantity=add_quantity)

        return HttpResponse("Added!")

    total = 0
    for cardincart in cart.cardincart_set.all():
        total += cardincart.card.price * cardincart.quantity

    cardlist = cart.card_list.all()

    for card in cardlist:
        cardincart = CardInCart.objects.get(cart=cart,card=card)
        card.price = cardincart.quantity * card.price
        card.quantity = cardincart.quantity


    context = {'cardlist': cardlist, 'total': total}

    return render(request, 'shopping_cart.html', context)


def get_billing(request):
    if request.session.get('billing_info_id', False):
        billing_info = BillingInformation.objects.get(pk=request.session.get('billing_info_id'))
    else:
        billing_info = BillingInformation()
        billing_info.save()
        request.session['billing_info_id'] = billing_info.id

    return billing_info


def get_shipping(request):
    if request.session.get('shipping_info_id', False):
        shipping_info = ShippingInformation.objects.get(pk=request.session.get('shipping_info_id'))
    else:
        shipping_info = ShippingInformation()
        shipping_info.save()
        request.session['shipping_info_id'] = shipping_info.id
    return shipping_info


def get_cart(request):
    if request.session.get('cart_id', False):
        cart = Cart.objects.get(pk=request.session.get('cart_id'))
    else:
        cart = Cart()
        cart.save()
        request.session['cart_id'] = cart.id

    return cart

def card_details(request):

    if request.method == 'POST':
        card_id = request.POST.get('card_id')
        chosen_id = int( request.POST.get('chosen_id') )
        if not chosen_id == 0:
            chosen = Card.objects.get(pk=chosen_id)
        else:
            chosen = None
        details = CardDetails.objects.get(pk=card_id)

        other_cards = Card.objects.filter(card_details=details).exclude(pk=chosen_id).order_by('price', 'wear')

        context = {'details': details, 'chosen': chosen, 'other_cards': other_cards}
        return render(request, 'card_details.html', context)

    return render(request, 'card_details.html')

def search_body(request):

    cards = CardDetails.objects.all()

    if request.method == 'POST':

        page = request.POST.get('page')
        search_text = request.POST.get('search_text')
        wears = request.POST.getlist('wear')
        printings = request.POST.getlist('printing')
        card_types = request.POST.getlist('type')
        card_colors = request.POST.getlist('color')
        card_rarities = request.POST.getlist('rarity')
        card_sets = request.POST.getlist('set')

        if search_text:
            cards = cards.filter(name__icontains=search_text)
        if card_types:
            cards = cards.filter(type__in=card_types)
        if card_colors:
            cards = cards.filter(color__in=card_colors)
        if card_rarities:
            cards = cards.filter(rarity__in=card_rarities)
        if card_sets:
            cards = cards.filter(set__in=card_sets)

    else:
        page = 2


    paginator = Paginator(cards, 7)

    try:
        cards = paginator.page(page)
    except PageNotAnInteger:
        cards = paginator.page(1)
    except EmptyPage:
        cards = paginator.page(paginator.num_pages)


    for card in cards:
        individuals = Card.objects.filter(card_details=card)
        card.total_quantity = 0
        card.seller_count = 0
        if wears:
            individuals = individuals.filter(wear__in=wears)
        if printings:
            individuals = individuals.filter(printing__in=printings)
        if individuals:
            for individ in individuals:
                card.total_quantity += individ.quantity
                card.seller_count += 1
            cheapest = individuals.order_by('price', 'wear').first()
            card.cheapest_card = cheapest



    context = {'cards': cards }

    return render(request, 'search_body.html', context)


def submit_order(request):
    cart = get_cart(request)

    cart.card_list.clear()
    return render(request, 'checkout.html')

def search(request):

    filters = {'wear': Card._meta.get_field('wear').choices, 'print': CardPrint.objects.all(), 'color': CardColor.objects.all(),
               'rarity': CardRarity.objects.all(), 'set': CardSet.objects.all(), 'type': CardType.objects.all()}

    search_text = None
    if request.method == 'POST':
        search_text = request.POST.get('search_text')

    context = {'filters': filters, 'search_text': search_text}
    return render(request, 'search.html', context)



def add_seller(request):

    if request.method == 'POST':
        form = AddSellerForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            seller = Seller(name=data["name"])
            seller.save()

    form = AddSellerForm()
    sellers = Seller.objects.all()
    context = {'form': form, 'sellers': sellers}

    return render(request, 'admin/add_seller.html', context)



def add_card_details(request):
    if request.method == 'POST':
        mode = request.POST.get('submit')
        form = AddCardDetailsForm(request.POST)
        if mode == 'Preview':
            # want to keep the form populated, send it back to template
            context = {'form': form}
            return render(request, 'admin/add_card_details.html', context)
        elif mode == 'Submit':
            if form.is_valid():
                data = form.cleaned_data
                card_details = CardDetails(front_art=data['front_art'],
                                           back_art=data['back_art'],
                                           name=data['name'],
                                           set=data['set'],
                                           rarity=data['rarity'],
                                           type=data['type'])
                card_details.save()
                # '*' converts to list
                card_details.formats.add(*data['formats'].all())
                card_details.color.add(*data['color'].all())


    form = AddCardDetailsForm()
    context = {'form': form}
    return render(request, 'admin/add_card_details.html', context)


def add_card(request):
    if request.method == 'POST':
        form = AddCardForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = request.user
            store = Store.objects.filter(owner=user).get()
            card = Card(card_details=data['card_details'],
                        wear=data['wear'],
                        printing=data['printing'],
                        price=data['price'],
                        quantity=data['quantity'],
                        store=store)
            card.save()
            return my_store(request)

    form = AddCardForm()

    context = {'form': form}
    return render(request, 'admin/add_card.html', context)