//create singleton to namespace js
if (!projectlight) {
  var projectlight = {};
}

//set up initial page variables - cached Jquery variables
projectlight.init = function(){

	//temporary debugging element to allow developer to see exact screen width during development
	$("body").append("<p style='color:red;z-index:100;position:absolute;top:5px;left:5px' id='pagewidth'></p>")

	//caching variables to refer to DOM elements in code
	projectlight.$window = $(window);
	projectlight.$wrap = $(".campl-wrap");
	projectlight.$rows = $(".campl-row");

	//header items
	projectlight.$globalHdrCtrl = $("#global-header-controls");
	projectlight.$siteSearchBtn = $("#site-search-btn");
	projectlight.$quicklinks = $(".campl-quicklinks");

	//navigation items
	projectlight.$globalNavOuter = $(".campl-global-navigation-outer");
	projectlight.$globalNavLI = $(".campl-global-navigation li");

	//instantiate footer columns on page load
	projectlight.$localFooter = $('.campl-local-footer');
	projectlight.$globalFooter = $('.campl-global-footer');

	projectlight.$localFooterColumns = projectlight.$localFooter.find('.campl-column3');
	projectlight.$globalFooterColumns = projectlight.$globalFooter.find('.campl-column3');

	//set namespaced variable to determine layout of menu
	//using modernizr to detect if media query is valid and has been triggered
	if(Modernizr.mq('only screen and (max-width: 767px)')){
		projectlight.mobileLayout  = true;

		//call function to remove uniform column height in footers for mobile layout
		projectlight.removeGlobalNavigationColumnHeight();
		projectlight.removeNavigationColumnHeight();
		projectlight.removeSectionListChildrenColumnHeight();
		projectlight.removeContentColumnHeight();
		projectlight.removeFooterColumnsHeight();

	}else{
		projectlight.mobileLayout  = false;

		//call function to create uniform column height in footers for desktop/tablet users
		projectlight.setGlobalNavigationColumnHeight();
		projectlight.setNavigationColumnHeight();
		projectlight.setSectionListChildrenColumnHeight();
		// Can't call setContentColumnHeight() until the page has loaded
		//projectlight.setContentColumnHeight();
		projectlight.setFooterColumnsHeight();
	}

	//if media queries are not supported set a fixed width container to prevent fluid layout breaking in IE and other browsers which do no support MQ
	if(!Modernizr.mq('only all')){
		projectlight.$wrap.addClass("campl-fixed-container");
	}

	//dynamically append Global navigation controls for javascript
	projectlight.$siteSearchBtn.prepend('<a href="#" class="campl-icon-search-btn ir" id="open-search">Search</a>');
	projectlight.$quicklinks.prepend('<a href="#" class="campl-open-quicklinks clearfix"><span class="campl-quicklinks-txt">Quick links</span><span class="campl-icon-dropdown ir"></span></a>')
	projectlight.$globalNavOuter.append('<a href="#" class="campl-close-menu" >Close</a>')

	//cache variables for DOM elements
	projectlight.$searchDrawer = $('.campl-search-drawer')
	projectlight.$navigationDrawer = $('.campl-global-navigation-drawer')


	//Bound click event to global nav button for mobile users to allow them to open the navigation in side drawer
	$("#open-menu").bind('click', function(e){
		//shut other open panels search and quicklinks
		projectlight.$searchDrawer.removeClass("campl-search-open");
		projectlight.$quicklinks.removeClass("campl-quicklinks-open");
		//close main navigation drawer
		projectlight.$globalNavOuter.removeClass("campl-drawer-open");
		//deselect any previously clicked links
		projectlight.$globalNavLI.removeClass("campl-selected");

		$("body").toggleClass("campl-navigation-open"); //added class to body instead so whole page can be moved to the right
		e.preventDefault();
	})

	$(".campl-close-menu").bind('click', function(e){
		//close main navigation drawer
		$(e.target).parent().removeClass("campl-drawer-open");
		//remove selected class from nav item clicked
		$(".campl-global-navigation li").removeClass("campl-selected")
		e.preventDefault();

	})


	//bound click event to primary navigation items for desktop view to allow users to browse the navigation in a megadropdown
	//the campl-no-drawer items are links that click straight through to a page instead of opening a mega dropdown
	$(".campl-global-navigation a").not(".campl-no-drawer").bind('click', function(e){
		var linkClicked = $(e.target);
		linkClicked.parent().addClass("campl-selected");
		var $drawer = $(linkClicked.attr('href'));

		//shut other open panels search and quicklinks
		projectlight.$searchDrawer.removeClass("campl-search-open");
		projectlight.$quicklinks.removeClass("campl-quicklinks-open");

		//if the navigation is open, and the drawer showing is the same as the link clicked then close drawer and close navigation container
		if($drawer.hasClass("campl-drawer-open")){
			projectlight.$globalNavLI.removeClass("campl-selected");
			projectlight.$navigationDrawer.removeClass("campl-navigation-open");
			projectlight.$globalNavOuter.removeClass("campl-drawer-open");
		}else{
			//else show close existing drawer and show new drawer, keep open navigation container

			//close any other drawers that are open
			projectlight.$globalNavOuter.not($drawer).removeClass("campl-drawer-open");
			//deselect any previously clicked links
			projectlight.$globalNavLI.not(linkClicked.parent()).removeClass("campl-selected");

			//toggle the open drawer class
			projectlight.$navigationDrawer.addClass("campl-navigation-open");
			$drawer.toggleClass("campl-drawer-open");
		}

		e.preventDefault();
	})

	//Show page elements which have been hidden to handle FOUC
	projectlight.$globalHdrCtrl.show();

	//fake last psuedo class to help layout in IE8. This removes the double borders from nested LI
	//which was visually confusing
	$(".campl-section-list-children ul").each(function(){
		$(this).find("li").last().addClass("campl-last")
	})

}


projectlight.setGlobalNavigationColumnHeight = function(){
	//for each section, get children, measure height of each, set height of each child
	$(".campl-global-navigation-outer").each(function(){
		var $childrenOfList = $(this).find(".campl-global-navigation-container");
		var maxColumnHeight = Math.max($childrenOfList.eq(0).height(), $childrenOfList.eq(1).height(), $childrenOfList.eq(2).height());

		//why is the col height 0 here?
		// console.log(maxColumnHeight)
		//hardcoded to 300 for time being
		$childrenOfList.css({'min-height':300} )
	})
}

projectlight.removeGlobalNavigationColumnHeight = function(){
	$('.campl-global-navigation-container').removeAttr("style");
}

projectlight.setSectionListChildrenColumnHeight = function(){
	//for each section list, get section-list-children, measure height of each, set height of each child
	$(".campl-section-list-row").each(function(){
		var $childrenOfList = $(this).find(".campl-section-list-children");
		var maxColumnHeight = Math.max($childrenOfList.eq(0).height(), $childrenOfList.eq(1).height(), $childrenOfList.eq(2).height());
		$childrenOfList.css({'min-height':maxColumnHeight} )
	})
}

projectlight.removeSectionListChildrenColumnHeight = function(){
	$('.campl-section-list-children').removeAttr("style");
}

projectlight.setNavigationColumnHeight = function(){
	//reset all values to begin with to ensure layout is changing on ipad orientation change
	$('.campl-global-navigation li a').removeAttr("style");

	var maxColumnHeight = Math.max($('.campl-global-navigation li a').eq(0).height(), $('.campl-global-navigation li a').eq(1).height(), $('.campl-global-navigation li a').eq(2).height());
	$('.campl-global-navigation li a').css({'min-height':maxColumnHeight} )
};

//force main content column min-height to the same height as the navigation column
projectlight.setContentColumnHeight = function(){

	//reset before adding further height
	$('.campl-tertiary-navigation, .campl-secondary-content, .campl-main-content').removeAttr("style");

	var carouselHeight  = 0;
	var maxColumnHeight = 0;
	if($('.campl-secondary-content').hasClass("campl-recessed-secondary-content")){
		// DPC: height() doesn't work here even with window.onload.
		//carouselHeight = $("#campl-slides").height();
		carouselHeight = 431;
		maxColumnHeight = Math.max(
			$('.campl-secondary-content').height()-carouselHeight,
			$('.campl-tertiary-navigation').height(),
			$('.campl-main-content').height(),
			$("#falcon-teasers").height(),
			$("#falcon-teasers-sub-column").height()
		);
	} else {
		maxColumnHeight = Math.max(
			$('.campl-secondary-content').height(),
			$('.campl-tertiary-navigation').height(),
			$(".campl-main-content").height()
		);
        }


	if($('.campl-tertiary-navigation').length > 0){
		$('.campl-tertiary-navigation, .campl-main-content').css({'min-height':maxColumnHeight} )
		$('.campl-secondary-content,').css({'min-height':maxColumnHeight+carouselHeight} )
	}else{
		$('.campl-tertiary-navigation, .campl-secondary-content, .campl-main-content').css({'min-height':maxColumnHeight} )
		$('.campl-secondary-content').css({'min-height':maxColumnHeight + carouselHeight } 	)
	}

	$('.campl-secondary-content').show();
};

projectlight.removeNavigationColumnHeight = function(){
	//had to remove style attribute, as setting height back to auto would not work
	$('.campl-global-navigation li a').removeAttr("style");
};

projectlight.removeContentColumnHeight = function(){
	//had to remove style attribute, as setting height back to auto would not work
	$('.campl-tertiary-navigation, .campl-secondary-content, .campl-main-content').removeAttr("style");
	$('.campl-secondary-content, .campl-main-content').show();
};

projectlight.setFooterColumnsHeight = function(){
	var highestglobalFooter = Math.max(projectlight.$globalFooterColumns.eq(0).height(), projectlight.$globalFooterColumns.eq(1).height(),projectlight.$globalFooterColumns.eq(2).height(),projectlight.$globalFooterColumns.eq(3).height())
	var highestLocalFooter = Math.max(projectlight.$localFooterColumns.eq(0).height(), projectlight.$localFooterColumns.eq(1).height(),projectlight.$localFooterColumns.eq(2).height(),projectlight.$localFooterColumns.eq(3).height())

	projectlight.$localFooterColumns.height(highestLocalFooter);
	projectlight.$globalFooterColumns.height(highestglobalFooter);
};

projectlight.removeFooterColumnsHeight = function(){
	projectlight.$localFooter.height("auto");
	projectlight.$localFooterColumns.height("auto");
	projectlight.$globalFooterColumns.height("auto");
};




projectlight.initTables = function(){
	/* FULLY EXPANDED RESPONSIVE TABLE SOLUTION */
	//responsive table solution
	var $tableContainer = $(".campl-responsive-table");

	//cycle through all responsive tables on page to instantiate open link
	$tableContainer.each(function (i) {
		var $table = $(this).find("table");
		var summary = "";

		//hide table
		$table.hide(); //might have to use positioning to prevent it being hidden from screen readers

		//suck out caption and summary to display above link
		var openTable = "<div class='campl-open-responsive-table'><a href='#' class='campl-open-responsive-table-link'>Click to open table " + $table.find("caption").text() + "</a>"+ summary + "</div>"

		//insert button to open table in page
		$(this).prepend(openTable);

		//create collapse button and hide until table is opened
		$(this).find('.campl-open-responsive-table').append("<a href='#' class='campl-collapse-table'>Collapse table</a>");

		$('.campl-collapse-table').hide();

		//collapse table and restore open link to user
		$(this).find('.campl-collapse-table').bind("click", function(e){
			var $tableContainer = $(e.target).parent().parent();
			$tableContainer.removeClass("campl-expanded-table");
			$table.removeClass("campl-full-width-table").hide();
			//show appropriate open link
			$(e.target).parent().find('.campl-open-responsive-table-link').show();
			//hide collapse link
			$(e.target).hide();
			e.preventDefault();
		})


		//open table on bind click event
		$(this).find(".campl-open-responsive-table-link").bind("click", function(e){
			$(e.target).parent().parent().addClass("campl-expanded-table");
			$table.addClass("campl-full-width-table");
			$table.show();
			//show appropriate close link
			$(e.target).parent().find('.campl-collapse-table').show();
			//hide open link
			$(e.target).hide();
			e.preventDefault();
		});

	})

	/* VERTICAL STACKING TABLE */
	var $verticalTable = $(".campl-vertical-stacking-table");

	//cycle through every vertical table on the page and insert table headers into table cells for mobile layout
	$verticalTable.each(function (i) {
		//for vertical stacking tables need to read the text value of each TH in turn and assign to the headers array
		var $tableHeaders = $(this).find('thead').find("th");

		var headerTextArray = [];
		//insert th value into every data set row in order
		//each loop to push into data array
		$tableHeaders.each(function (i) {
			headerTextArray.push($(this).text());
		});

		//for every row, insert into td append before text in td insert span to handle styling of header and data
		var $verticalTableRows = $(this).find("tr");

		$verticalTableRows.each(function (i) {
			//need to find all children of the table rows, (and not just table data cells)
			var $tableCells = $(this).children();
			$tableCells.each(function (i) {
				$(this).prepend("<span class='campl-table-heading'>"+headerTextArray[i]+"</span>")
			})

		})

	})

}



//DOM ready
$(document).ready(function() {

	//instantiate all the DOM elements which require javascript rendering
	projectlight.init();
	projectlight.initTables();

	//remove click event from local nav children selected items

	$(".campl-vertical-breadcrumb-children .campl-selected a").bind("click", function(e){
		e.preventDefault()
	})

	//instantiate calendar
	if(document.getElementById('calendar')){
		$("#calendar").Zebra_DatePicker({
		    always_visible: $('.calendar-container'),
			format: 'dd mm yyyy',
			direction: true,
			always_show_clear:false,
			disabled_dates: ['15 09 2012']
		});
	}

	//Change event for mobile navigation list selector
	if(document.getElementById('navigation-select')){
		$("#navigation-select").bind("change", function(e){
			window.location = $(this).val()
		})
	}


	$(".campl-notifications-panel").each(function(){
		var $thisElem = $(this);
		$thisElem.append("<a href='#' class='ir campl-close-panel'>Close panel</a>");
		$thisElem.find('.campl-close-panel').bind("click", function(e){
			$(e.target).parent().remove();
			e.preventDefault();
		})
	})


	//bound click events for twitter bootstrap pills and tab elements
	$('#navTabs a').click(function (e) {
	  e.preventDefault();
	  $(this).tab('show');
	})

	$('#navPills a').click(function (e) {
	  e.preventDefault();
	  $(this).tab('show');
	})

	$('#searchTabs a').click(function (e) {
	  e.preventDefault();
	  $(this).tab('show');
	})



	//instantiate height of buttons for mobile users, on carousel object
	if(document.getElementById('campl-carousel')){
		projectlight.createCarousel();
		//wait for DOM ready to resize buttons for mobile
		if(Modernizr.mq('only screen and (max-width: 767px)')){
			$(".campl-carousel-controls a").height($(".image-container").height())
		}else{
			$(".campl-carousel-controls a").attr("style", "")
		}
	}


	//resize event handles changing flag layout to determine if user mode is mobile or not
	//If the mode has changed the re-rendering or reset functions will be called to change the page layout
	projectlight.$window.resize(function() {

		if(document.getElementById('campl-carousel')){
			projectlight.resetCarousel();

			//truncate homepage carousel content if page is thinner
			if(Modernizr.mq('only screen and (min-width: 768px) and (max-width: 1000px)')){

				//carousel height is remaining as if text isn't being truncated

				projectlight.$slideCaption.each(function(i){
						$(this).text($.trim(projectlight.slideCaptionItems[i]).substring(0, 50).split(" ").slice(0, -1).join(" ") + "...")
					})

					projectlight.$carouselContent.each(function(i){
						$(this).text($.trim(projectlight.carouselContentItems[i]).substring(0, 35).split(" ").slice(0, -1).join(" ") + "...")
					})
			}else{

				projectlight.$slideCaption.each(function(i){
					$(this).text(projectlight.slideCaptionItems[i]);
				})

				projectlight.$carouselContent.each(function(i){
					$(this).text(projectlight.carouselContentItems[i]);
				})
			}

		}

		//commented out debugging to help developers see page width during development
		//$("#pagewidth").html($(window).width());


		//check size of columns on resize event and remove incase of mobile layout
		if(Modernizr.mq('only all')){
			//if mobile layout is triggered in media queries
			if(Modernizr.mq('only screen and (max-width: 767px)')){
				//if layout moves from desktop to mobile layout
				if(!projectlight.mobileLayout){
					//set current state flag
					projectlight.mobileLayout  = true;
					//reset main nav to un-open state
					projectlight.$navigationDrawer.removeClass("campl-navigation-open");
					projectlight.$globalNavOuter.removeClass("campl-drawer-open");
					projectlight.$searchDrawer.removeClass("campl-search-open");
					//deselect any previously clicked links
					projectlight.$globalNavLI.removeClass("campl-selected");

				}

				// if media queries are supported then remove columns on mobile layout
				projectlight.removeGlobalNavigationColumnHeight();
				projectlight.removeNavigationColumnHeight();
				projectlight.removeContentColumnHeight();
				projectlight.removeSectionListChildrenColumnHeight();
				projectlight.removeFooterColumnsHeight();

				//set height of carousel buttons
				$(".campl-carousel-controls a").height($(".image-container").height())

				projectlight.mobileLayout  = true;
			}else{ //desktop layout code
				//if page width moves from mobile layout to desktop
				if(projectlight.mobileLayout){
					//set current state flag
					projectlight.mobileLayout  = false;

					//close global nav drawer
					$("body").removeClass("campl-navigation-open");
				}
				projectlight.setGlobalNavigationColumnHeight();
				projectlight.setNavigationColumnHeight();
				projectlight.setSectionListChildrenColumnHeight();
				projectlight.setFooterColumnsHeight();

				//remove fixed height on carousel buttons
				//set height of carousel buttons
				$(".campl-carousel-controls a").attr("style", "")

				projectlight.mobileLayout  = false;
			}
		}
	})



})

// Call setContentColumnHeight() on page load. This comes after the document
// ready initialisation above, when whole page has been loaded, including
// images that might affect the content height.
$(window).load(projectlight.setContentColumnHeight)
