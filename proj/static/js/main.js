jQuery(document).ready(function($) {
    "use strict";

    //menu change icon and dropdown
    $(".js-menubar li .js-plus-icon").on("click", function() {
        $(this).toggleClass('minus');
        $(this).parent().find(".dropdown-menu").slideToggle(function() {
            $(this).next().stop(true).toggleClass('open', $(this).is(":visible"));
        });
    });

    $(".js-filter-menu li .js-plus-icon").on("click", function() {
        $(this).toggleClass('minus');
        $(this).parent().find(".filter-menu").slideToggle(function() {
            $(this).next().stop(true).toggleClass('open', $(this).is(":visible"));
        });
    });

    $(".js-faq .faq-content .js-plus-icon").on("click", function() {
        $(this).toggleClass('minus');
        $(this).parent().find(".faq-answer").slideToggle(function() {
            $(this).next().stop(true).toggleClass('open', $(this).is(":visible"));
        });
    });
    // Open menu dropdown home 5
    $(".js-menubar > li > a").on("click", function() {
        $(this).toggleClass('active');
        $(this).parent().find(".js-open-menu").slideToggle(function() {
            $(this).next().stop(true).toggleClass('open', $(this).is(":visible"));
        });
    });
    // Push menu home 5
    var menuLeft = $('.pushmenu-left');
    var menuHome6 = $('.menu-home5');
    var nav_list = $('.topbar-cart .icon-cart');
    var nav_click = $('.icon-pushmenu');
    nav_list.on("click", function(event) {
        event.stopPropagation();
        $(this).toggleClass('active');
        $('body').toggleClass('pushmenu-push-toright-cart');
        menuLeft.toggleClass('pushmenu-open');
        $(".container").toggleClass("canvas-container");
    });
    nav_click.on("click", function(event) {
        event.stopPropagation();
        $(this).toggleClass('active');
        $('body').toggleClass('pushmenu-push-toleft');
        menuHome6.toggleClass('pushmenu-open');
    });
    $(".wrappage").on("click", function() {
        $(this).removeClass('active');
        $('body').removeClass('pushmenu-push-toright-cart').removeClass('pushmenu-push-toleft');
        menuLeft.removeClass('pushmenu-open');
        menuHome6.removeClass('pushmenu-open');
    });
    $(".close-left").on("click", function() {
        $(this).removeClass('active');
        $('body').removeClass('pushmenu-push-toright-cart');
        menuLeft.removeClass('pushmenu-open');
    });
    $(".close-left").on("click", function() {
        $('body').removeClass('pushmenu-push-toleft');
        menuHome6.removeClass('pushmenu-open');
    });
    // SHOPPING CART Quantity increment buttons

    var quantitiy = 0;
    $('.js-plus').on("click", function(e) {

        // Stop acting like a button
        e.preventDefault();
        // Get the field name
        var quantity = parseInt($('.js-number').val(), 10);

        // If is not undefined

        $('.js-number').val(quantity + 1);


        // Increment    
    });

    $('.js-minus').on("click", function(e) {
        // Stop acting like a button
        e.preventDefault();
        // Get the field name
        var quantity = parseInt($('.js-number').val(), 10);

        // If is not undefined

        // Increment
        if (quantity > 0) {
            $('.js-number').val(quantity - 1);
        }
    });

    //SHOP LISTING FILTER
    // Price Slider
    if ($('.price-slider').length > 0) {
        $('.price-slider').slider({
            min: 100,
            max: 700,
            step: 10,
            value: [100, 400],


        });
    }
    //SHOP GRID
    $(".view-mode .col").on("click", function() {
        $(this).toggleClass('active');
        $(".product-grid").removeClass("product-list");

        $(".view-mode .list").removeClass("active");
    });
    $(".view-mode .list").on("click", function() {
        $(this).toggleClass("active");
        $(".product-grid").addClass("product-list");

        $(".view-mode .col").removeClass("active");
    });
    // Open zipcode
    $(".calculate").on('click', function() {
        $(this).next().slideToggle();
        $(this).toggleClass("active");
    });
    // Checkout : open login box
    $(".js-showlogin").on('click', function() {
        $(".js-openlogin").slideToggle();
        $(this).toggleClass("active");
    });
    // Checkout : open coupon
    $(".js-showcp").on('click', function() {
        $(".js-opencp").slideToggle();
        $(this).toggleClass("active");

    });
    // Checkout : open pick-up point
    $(".js-show-pickup-point").on('click', function() {
        if ($(".js-show-courier-delivery").hasClass('active')){
            $(".js-open-courier-delivery").slideToggle();
            $(".js-show-courier-delivery").removeClass("active");
        };
        if ($(".js-show-pickup-from-the-store").hasClass('active')){
            $(".js-open-pickup-from-the-store").slideToggle();
            $(".js-show-pickup-from-the-store").removeClass("active");
        };
        $(".js-open-pickup-point").slideToggle();
        $(this).toggleClass("active");
        document.getElementById("pickup-point-region").required = true;
        document.getElementById("pickup-point-city").required = true;
        document.getElementById("courier-delivery-region").required = false;
        document.getElementById("courier-delivery-city").required = false;
        document.getElementById("courier-delivery-street").required = false;
        document.getElementById("courier-delivery-house").required = false;
    });
    // Checkout : open courier delivery
    $(".js-show-courier-delivery").on('click', function() {
        if ($(".js-show-pickup-point").hasClass('active')){
            $(".js-open-pickup-point").slideToggle();
            $(".js-show-pickup-point").removeClass("active");
        };
        if ($(".js-show-pickup-from-the-store").hasClass('active')){
            $(".js-open-pickup-from-the-store").slideToggle();
            $(".js-show-pickup-from-the-store").removeClass("active");
        };
        $(".js-open-courier-delivery").slideToggle();
        $(this).toggleClass("active");
        document.getElementById("courier-delivery-region").required = true;
        document.getElementById("courier-delivery-city").required = true;
        document.getElementById("courier-delivery-street").required = true;
        document.getElementById("courier-delivery-house").required = true;
        document.getElementById("pickup-point-region").required = false;
        document.getElementById("pickup-point-city").required = false;
    });
    // Checkout : open pickup from the store
    $(".js-show-pickup-from-the-store").on('click', function() {
        if ($(".js-show-courier-delivery").hasClass('active')){
            $(".js-open-courier-delivery").slideToggle();
            $(".js-show-courier-delivery").removeClass("active");
        };
        if ($(".js-show-pickup-point").hasClass('active')){
            $(".js-open-pickup-point").slideToggle();
            $(".js-show-pickup-point").removeClass("active");
        };
        $(".js-open-pickup-from-the-store").slideToggle();
        $(this).toggleClass("active");
        document.getElementById("pickup-point-region").required = false;
        document.getElementById("pickup-point-city").required = false;
        document.getElementById("courier-delivery-region").required = false;
        document.getElementById("courier-delivery-city").required = false;
        document.getElementById("courier-delivery-street").required = false;
        document.getElementById("courier-delivery-house").required = false;
    });
    //Open filter
    $(".js-filter").on('click', function() {
        $(".js-filter-open").show();

    });
    //Open filter
    $(".js-close").on('click', function(e) {
        e.preventDefault();
        $(".js-filter-open").hide();
        return false;
    });
    // Scroll slider

    $('.scroll-down').on('click', function() {
        $('html, body').animate({ scrollTop: $('section#main-content').offset().top }, 'slow');
        return false;
    });
    // Scroll to TOP
    $(window).scroll(function() {
        if ($(this).scrollTop() > 100) {
            $('.scroll_top').fadeIn();
        } else {
            $('.scroll_top').fadeOut();
        }
    });

    $('.scroll_top').on('click', function() {
        $("html, body").animate({
            scrollTop: 0
        }, 600);
        return false;
    });
    $(window).scroll(function() {
        var scroll = $(window).scrollTop();

        if (scroll > 500) {
            $(".intro").hide();
            $(".scroll_down").hide();
        }
    });
    // scroll down
    $(".scroll_down").on('click', function(e) {
        e.preventDefault();
        $(".intro").hide();
        $(this).hide();
        return false;
    });
    // Js product single slider
    $('.js-click-product').slick({
        slidesToShow: 6,
        slidesToScroll: 1,
        asNavFor: '.js-product-slider',
        dots: false,
        arrows: false,
        focusOnSelect: true,
        infinite: true,
        variableWidth: true
    });
    $('.js-product-slider').slick({
        slidesToShow: 1,
        slidesToScroll: 1,
        arrows: false,
        asNavFor: '.js-click-product'
    });

    // Js product single slider
    $('.js-click-product-v2').slick({
        slidesToShow: 3,
        slidesToScroll: 1,
        asNavFor: '.js-product-slider-v2',
        dots: false,
        arrows: false,
        focusOnSelect: true,
        infinite: true
    });
    $('.js-product-slider-v2').slick({
        slidesToShow: 1,
        slidesToScroll: 1,
        arrows: false,
        asNavFor: '.js-click-product-v2'
    });
    // Js product single slider fw
    $('.js-click-product-fw').slick({
        slidesToShow: 3,
        slidesToScroll: 1,
        asNavFor: '.js-product-slider-fw',
        dots: false,
        arrows: false,
        focusOnSelect: true,

    });
    $('.js-product-slider-fw').slick({
        slidesToShow: 1,
        slidesToScroll: 1,
        arrows: false,
        asNavFor: '.js-click-product-fw'
    });
    // product carousel
    $('.js-owl-product').owlCarousel({
        margin: 30,
        autoplay: true,
        autoplayTimeout: 3000,
        loop: true,
        nav: true,
        navText: ["<span class='fa fa-angle-left'></span>", "<span class='fa fa-angle-right'></span>"],
        responsive: {
            0: {
                items: 1
            },
            480: {
                items: 2
            },
            1000: {
                items: 5
            }
        }
    });

    // product list homebs
    $('.js-owl-product-homebs').owlCarousel({
        margin: 70,
        autoplay: true,
        autoplayTimeout: 3000,
        loop: true,
        nav: false,
        dots: false,
        responsive: {
            0: {
                items: 1
            },
            480: {
                items: 2
            },
            1000: {
                items: 3
            }
        }
    });
    // Instagram carousel
    $('.js-owl-instagram').owlCarousel({
        margin: 0,
        autoplay: true,
        autoplayTimeout: 3000,
        loop: true,
        nav: false,
        navText: ["", ""],
        dots: false,
        responsive: {
            0: {
                items: 1
            },
            480: {
                items: 2
            },
            1000: {
                items: 5
            }
        }
    });
    $('.js-insta-blog').owlCarousel({
        margin: 6,
        autoplay: true,
        autoplayTimeout: 3000,
        loop: true,
        nav: true,
        navText: ["<span class='fa fa-angle-left'></span>", "<span class='fa fa-angle-right'></span>"],
        dots: false,
        responsive: {
            0: {
                items: 1
            },
            480: {
                items: 2
            },
            1000: {
                items: 4
            }
        }
    });
    // Slider category full-width
    $('.js-click-slider').slick({
        slidesToShow: 5,
        slidesToScroll: 1,
        asNavFor: '.js-slider',
        dots: false,
        arrows: false,
        focusOnSelect: true,
        afterChange: function(slickSlider, i) {
            //remove all active class
            $('.js-click-slider .slick-slide').removeClass('slick-active');
            //set active class for current slide
            $('.js-click-slider .slick-slide').eq(i).addClass('slick-active');
        }

    });
    //set active class to first slide
    $('.js-click-slider .slick-slide').eq(0).addClass('slick-active');
    $('.js-slider').slick({
        slidesToShow: 1,
        slidesToScroll: 1,
        arrows: false,
        asNavFor: '.js-click-slider'
    });
    $('.js-click-slider').on('mouseenter', '.slick-slide', function(e) {
        var $currTarget = $(e.currentTarget),
            index = $currTarget.data('slick-index'),
            slickObj = $('.js-slider').slick('getSlick');

        slickObj.slickGoTo(index);

    });
    // Slider home clean

    $('.js-homesimple-slider').slick({
        autoplay: false,
        dots: true,
        slidesToShow: 1,
        slidesToScroll: 1,

        customPaging: function(slider, i) {
            var thumb = $(slider.$slides[i]).data();
            return '<a>' + (i + 1) + '</a>';
        },
        responsive: [{
            breakpoint: 1200,
            settings: {
                dots: true,
                arrows: false,
                infinite: false,
                slidesToShow: 1,
                slidesToScroll: 1
            }
        }]
    });
    //Slider fullw
    $('.js-fullw').slick({
        autoplay: true,
        dots: true,
        arrows: false,
        slidesToShow: 1,
        slidesToScroll: 1,

        customPaging: function(slider, i) {
            var thumb = $(slider.$slides[i]).data();
            return '<a>' + (i + 1) + '</a>';
        },
        responsive: [{
                breakpoint: 1024,
                settings: {
                    slidesToShow: 1,
                    slidesToScroll: 1,
                    infinite: true,
                    dots: true
                }
            },
            {
                breakpoint: 600,
                settings: {
                    slidesToShow: 1,
                    slidesToScroll: 1,
                    dots: false
                }
            }

        ]
    });
    // Slider home category
    $('.js-homecate').slick({
        dots: true,
        arrows: true,
        infinite: true,
        slidesToShow: 1,
        slidesToScroll: 1
    });
    // Slider home Clean
    $('.js-homeclean-slider').slick({
        dots: true,
        arrows: false,
        slidesToShow: 1,
        slidesToScroll: 1
    });

    // brand carousel
    $('.js-owl-category').owlCarousel({
        loop: true,
        nav: true,
        navText: ["", ""],
        dots: false,
        responsive: {
            0: {
                items: 1
            },
            600: {
                items: 2
            },
            768: {
                items: 3
            },
            1000: {
                items: 5
            }
        }
    });
    // Js home lookbook
    $('.js-owl-loobook').owlCarousel({
        autoplayTimeout: 3000,
        autoplay: true,
        loop: true,
        margin: 30,
        nav: false,
        dots: false,
        responsive: {
            0: {
                items: 1
            },
            568: {
                items: 2
            },
            768: {
                items: 3
            },
            1000: {
                items: 3
            }
        }
    });
    // Js home clean blog
    $('.js-owl-blog').owlCarousel({
        loop: true,
        margin: 30,
        nav: true,
        navText: ["<span class='fa fa-angle-left'></span>", "<span class='fa fa-angle-right'></span>"],
        dots: false,
        responsive: {
            0: {
                items: 1
            },
            568: {
                items: 2
            },
            768: {
                items: 3
            },
            1000: {
                items: 3
            }
        }
    });
    // Js home  simple blog
    $('.js-owl-blog-v2').owlCarousel({
        loop: true,
        margin: 30,
        nav: true,
        navText: ["<span class='fa fa-angle-left'></span>", "<span class='fa fa-angle-right'></span>"],
        dots: false,
        responsive: {
            0: {
                items: 1
            },
            568: {
                items: 2
            },
            768: {
                items: 2
            },
            1000: {
                items: 2
            }
        }
    });
    // Js home lookbook 2
    $('.js-owl-lookbook-ver2').owlCarousel({
        autoplayTimeout: 3000,
        autoplay: true,
        loop: true,
        margin: 30,
        nav: false,
        dots: false,
        responsive: {
            0: {
                items: 1,

            },
            568: {
                items: 2
            },
            768: {
                items: 3
            },
            1000: {
                items: 5
            }
        }
    });

    $('.js-owl-blog-product').owlCarousel({
        autoplayTimeout: 3000,
        autoplay: true,
        loop: true,
        margin: 15,
        nav: true,
        navText: ["<span class='fa fa-angle-left'></span>", "<span class='fa fa-angle-right'></span>"],
        dots: false,
        responsive: {
            0: {
                items: 1,

            },
            568: {
                items: 2
            },
            768: {
                items: 4
            },
            1000: {
                items: 4
            }
        }
    });
    // JS owl category Carousel 
    $('.js-owl-category').owlCarousel({
        loop: true,
        margin: 0,
        nav: true,
        dots: false,
        responsive: {
            0: {
                items: 1,

            },
            568: {
                items: 2
            },
            768: {
                items: 3
            },
            1000: {
                items: 5
            }
        }
    });
    // JS owl team Carousel 
    $('.js-owl-team').owlCarousel({
        autoplayTimeout: 3000,
        autoplay: true,
        loop: true,
        margin: 30,
        nav: true,
        navText: ["<span class='fa fa-angle-left'></span>", "<span class='fa fa-angle-right'></span>"],
        dots: false,
        responsive: {
            0: {
                items: 1,

            },
            568: {
                items: 2
            },
            768: {
                items: 2
            },
            1000: {
                items: 3
            }
        }
    });
    // JS owl team Carousel 
    $('.js-owl-client').owlCarousel({
        autoplayTimeout: 3000,
        autoplay: true,
        loop: true,
        margin: 30,
        nav: false,
        dots: false,
        autoHeight:true,
        responsive: {
            0: {
                items: 1,

            },
            568: {
                items: 2
            },
            768: {
                items: 3
            },
            1000: {
                items: 5
            }
        }
    });
    // js quickview
    $('.js-quickview').slick({
        dots: true,
        infinite: true,
        arrows: true,
        speed: 300,
        slidesToShow: 1
    });
    // Shop Masonry

    $('.grid-flat').masonry({
        itemSelector: '.grid-item',
        columnWidth: '.grid-sizer',
        percentPosition: true
    });
    // blog Masonry
    $(window).load(function(){ 
        $('.gird-blog-masonry').masonry({
            itemSelector: '.grid-item',
            columnWidth: '.grid-sizer',
            percentPosition: true
        });
    });
    // lookbook masonry
    $('.wrap-gallery-masonry').masonry({
        itemSelector: '.wrap-gallery-item',
        columnWidth: '.grid-sizer',
        percentPosition: true
    });
    // sticky scroll
    if ($(".single-product-detail").hasClass("engoc-product-design-sticky")) {
    var s, o, i = $(".entry-summary"),
        n = i.find(".summary-inner"),
        r = i.width(),
        l = $(".product-images"),
        c = l.find(".shopify-product-gallery__wrapper a"),
        d = $(window).height(),
        u = l.outerHeight(),
        p = 130,
        h = 600,
        m = i.outerHeight(),
        f = $(window).scrollTop(),
        g = l.offset().top,
        v = i.offset().left + 15,
        w = g + u,
        b = f + p + m;
        i.css({ height: m }),
        $(window).resize(function() {
            d = $(window).height(),
                m = i.outerHeight(),
                u = l.outerHeight(),
                m < d - p ? i.addClass("in-viewport").removeClass("not-in-viewport") : i.removeClass("in-viewport").addClass("not-in-viewport"), f = $(window).scrollTop(),
                b = f + p + m,
                r = i.width(),
                v = i.offset().left + 15,
                g = l.offset().top,
                w = g + u, r > h && (v += o = (r - h) / 2),
                f + p >= g ? (i.addClass("block-sticked"),
                    n.css({ top: p, width: r, position: "fixed", transform: "translateY(-20px)" })) : (i.removeClass("block-sticked"),
                    n.css({ top: "auto", left: "auto", width: "auto", position: "relative", transform: "translateY(0px)" })),
                b > w ? i.addClass("hide-temporary") : i.removeClass("hide-temporary"), d = $(window).height(),
                c.each(function() { s = $(this).offset().top, f > s - d + 20 && ($(this).addClass("animate-images")) })
        }),
        $(window).scroll(function() {
            d = $(window).height(),
                c.each(function() { s = $(this).offset().top, f > s - d + 20 && ($(this).addClass("animate-images")) })

            f = $(window).scrollTop(),
                b = f + p + m,
                r = i.width(),
                v = i.offset().left + 15,
                g = l.offset().top,
                w = g + u, r > h && (v += o = (r - h) / 2),
                f + p >= g ? (i.addClass("block-sticked"),
                    n.css({ top: p, width: r, position: "fixed", transform: "translateY(-20px)" })) : (i.removeClass("block-sticked"),
                    n.css({ top: "auto", left: "auto", width: "auto", position: "relative", transform: "translateY(0px)" })),
                b > w ? i.addClass("hide-temporary") : i.removeClass("hide-temporary")

            d = $(window).height(),
                m = i.outerHeight(),
                u = l.outerHeight(),
                m < d - p ? i.addClass("in-viewport").removeClass("not-in-viewport") : i.removeClass("in-viewport").addClass("not-in-viewport"), d = $(window).height(),
                c.each(function() { s = $(this).offset().top, f > s - d + 20 && ($(this).addClass("animate-images")) }), d = $(window).height(),
                c.each(function() { s = $(this).offset().top, f > s - d + 20 && ($(this).addClass("animate-images")) })
        })
    }

    // STICKY HEADER
  
    $(window).scroll(function(e) {
        if($(window).width()>1199) {
          if($(window).scrollTop()>145) {     
            $('.header-v1 .header-top').addClass("fixed-header fadeInDown");  
            $('.header-v3 .topbar').addClass("fixed-header fadeInDown"); 
            $('.header-v4 .topbar').addClass("fixed-header fadeInDown");   
            $('.header-v5 .topbar').addClass("fixed-header fadeInDown");                   
          } else {
            $('.header-v1 .header-top').removeClass("fixed-header fadeInDown"); 
            $('.header-v3 .topbar').removeClass("fixed-header fadeInDown"); 
            $('.header-v4 .topbar').removeClass("fixed-header fadeInDown");  
            $('.header-v5 .topbar').removeClass("fixed-header fadeInDown");                 
         }
        }
    });

});