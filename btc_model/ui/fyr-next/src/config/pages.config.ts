import categoriesDb from '../mocks/db/categories.db';
import productsDb from '../mocks/db/products.db';
import usersDb from '../mocks/db/users.db';
import rolesDb from '../mocks/db/roles.db';
import projectsDb from '../mocks/db/projects.db';

export const examplePages = {
	examplesPage: {
		id: 'examplesPage',
		to: '/examples-page',
		text: 'Examples Page',
		icon: 'HeroBookOpen',
	},
	duotoneIconsPage: {
		id: 'duotoneIconsPage',
		to: '/duotone-icons',
		text: 'Duotone Icons',
		icon: 'HeroCubeTransparent',
	},
};

export const appPages = {
	strategyAppPages: {
		id: 'strategyApp',
		to: '/strategy',
		text: '量化策略',
		icon: 'HeroRocketLaunch',
		subPages: {
			strategyDashboardPage: {
				id: 'strategyDashboardPage',
				to: '/strategy/dashboard',
				text: '策略概览',
				icon: 'HeroChartBar',
			},
			crossExchangeArbitrage: {
				id: 'crossExchangeArbitrage',
				to: '/strategy/cross-exchange',
				text: '跨所套利策略',
				icon: 'HeroArrowsRightLeft',
				subPages: {
					signals: {
						id: 'crossExchangeSignals',
						to: '/strategy/cross-exchange/signals',
						text: '交易信号',
						icon: 'HeroBell',
					},
					orders: {
						id: 'crossExchangeOrders',
						to: '/strategy/cross-exchange/orders',
						text: '委托订单',
						icon: 'HeroClipboardDocumentList',
					},
					trades: {
						id: 'crossExchangeTrades',
						to: '/strategy/cross-exchange/trades',
						text: '成交订单',
						icon: 'HeroCheckCircle',
					},
					positions: {
						id: 'crossExchangePositions',
						to: '/strategy/cross-exchange/positions',
						text: '策略持仓',
						icon: 'HeroChartBar',
					},
				},
			},
			triangularArbitrage: {
				id: 'triangularArbitrage',
				to: '/strategy/triangular',
				text: '三角套利',
				icon: 'HeroTriangle',
				subPages: {
					signals: {
						id: 'triangularSignals',
						to: '/strategy/triangular/signals',
						text: '交易信号',
						icon: 'HeroBell',
					},
					orders: {
						id: 'triangularOrders',
						to: '/strategy/triangular/orders',
						text: '委托订单',
						icon: 'HeroClipboardDocumentList',
					},
					trades: {
						id: 'triangularTrades',
						to: '/strategy/triangular/trades',
						text: '成交订单',
						icon: 'HeroCheckCircle',
					},
					positions: {
						id: 'triangularPositions',
						to: '/strategy/triangular/positions',
						text: '策略持仓',
						icon: 'HeroChartBar',
					},
				},
			},
		},
	},
	// aiAppPages: {
	// 	id: 'aiApp',
	// 	to: '/ai',
	// 	text: '人工智能',
	// 	icon: 'HeroRocketLaunch',
	// 	subPages: {
	// 		aiDashboardPage: {
	// 			id: 'aiDashboardPage',
	// 			to: '/ai/dashboard',
	// 			text: 'AI Dashboard',
	// 			icon: 'HeroRocketLaunch',
	// 		},
	// 		chatPages: {
	// 			id: 'customerPage',
	// 			to: '/ai/chat',
	// 			text: 'Chat Pages',
	// 			icon: 'HeroChatBubbleLeft',
	// 			subPages: {
	// 				photoPage: {
	// 					id: 'photoPage',
	// 					to: '/ai/chat/photo',
	// 					text: 'Photo Editing',
	// 					icon: 'HeroPhoto',
	// 				},
	// 				videoPage: {
	// 					id: 'videoPage',
	// 					to: '/ai/chat/video',
	// 					text: 'Video Generation',
	// 					icon: 'HeroFilm',
	// 				},
	// 				audioPage: {
	// 					id: 'audioPage',
	// 					to: '/ai/chat/audio',
	// 					text: 'Audio Generation',
	// 					icon: 'HeroMusicalNote',
	// 				},
	// 				codePage: {
	// 					id: 'audioPage',
	// 					to: '/ai/chat/code',
	// 					text: 'Code Generation',
	// 					icon: 'HeroCommandLine',
	// 				},
	// 			},
	// 		},
	// 	},
	// },
	salesAppPages: {
		id: 'salesApp',
		to: '/sales',
		text: '销售',
		icon: 'HeroBanknotes',
		subPages: {
			salesDashboardPage: {
				id: 'salesDashboardPage',
				to: '/',
				text: 'Sales Dashboard',
				icon: 'HeroRectangleGroup',
			},
			productPage: {
				id: 'productPage',
				to: '/sales/product',
				text: '产品',
				icon: 'HeroRectangleStack',
				subPages: {
					listPage: {
						id: 'productsListPage',
						to: '/sales/product/list',
						text: 'Products List',
						icon: 'HeroQueueList',
					},
					editPage: {
						id: 'productPage',
						to: `/sales/product/${productsDb[0].id}`,
						text: `Product #${productsDb[0].id}`,
						icon: 'HeroTicket',
					},
					editPageLink: {
						id: 'editPageLink',
						to: '/sales/product',
					},
				},
			},
			categoryPage: {
				id: 'categoryPage',
				to: '/sales/category',
				text: 'Category',
				icon: 'HeroSquare2Stack',
				subPages: {
					listPage: {
						id: 'categoryListPage',
						to: '/sales/category/list',
						text: 'Category List',
						icon: 'HeroQueueList',
					},
					editPage: {
						id: 'productPage',
						to: `/sales/category/${categoriesDb[0].id}`,
						text: `Category #${categoriesDb[0].id}`,
						icon: 'HeroStop',
					},
					editPageLink: {
						id: 'editPageLink',
						to: '/sales/category',
					},
				},
			},
		},
	},
	crmAppPages: {
		id: 'crmApp',
		to: '/crm',
		text: 'CRM',
		icon: 'HeroUserGroup',
		subPages: {
			crmDashboardPage: {
				id: 'crmDashboardPage',
				to: '/crm/dashboard',
				text: 'CRM Dashboard',
				icon: 'HeroUserCircle',
			},
			customerPage: {
				id: 'customerPage',
				to: '/crm/customer',
				text: 'Customers',
				icon: 'HeroUserGroup',
				subPages: {
					listPage: {
						id: 'crmListPage',
						to: '/crm/customer/list',
						text: 'Customers List',
						icon: 'HeroQueueList',
					},
					editPage: {
						id: 'customerPage',
						to: `/crm/customer/${usersDb[0].id}`,
						text: `Customer @${usersDb[0].id}`,
						icon: 'HeroUser',
					},
					editPageLink: {
						id: 'editPageLink',
						to: '/crm/customer',
					},
				},
			},
			rolePage: {
				id: 'rolePage',
				to: '/crm/role',
				text: 'Roles',
				icon: 'HeroShieldCheck',
				subPages: {
					listPage: {
						id: 'crmListPage',
						to: '/crm/role/list',
						text: 'Role List',
						icon: 'HeroQueueList',
					},
					editPage: {
						id: 'customerPage',
						to: `/crm/role/${rolesDb[0].id}`,
						text: `Role @${rolesDb[0].id}`,
						icon: 'HeroShieldExclamation',
					},
					editPageLink: {
						id: 'editPageLink',
						to: '/crm/role',
					},
				},
			},
		},
	},
	projectAppPages: {
		id: 'projectApp',
		to: '/project',
		text: 'Project',
		icon: 'HeroClipboardDocumentCheck',
		subPages: {
			projectDashboardPage: {
				id: 'projectDashboardPage',
				to: '/project/dashboard',
				text: 'Projects Dashboard',
				icon: 'HeroClipboardDocumentCheck',
			},
			projectBoardPage: {
				id: 'projectBoardPage',
				to: `/project/board/${projectsDb[0].id}`,
				text: `Board ${projectsDb[0].name}`,
				icon: 'HeroQrCode',
			},
			projectBoardPageLink: {
				id: 'projectBoardPageLink',
				to: '/project/board',
			},
		},
	},
	educationAppPages: {
		id: 'educationApp',
		to: '/education',
		text: '知识库',
		icon: 'HeroAcademicCap',
		subPages: {
			educationDashboardPage: {
				id: 'educationDashboardPage',
				to: '/education/dashboard',
				text: '量化策略概览',
				icon: 'HeroChartBar',
			},
			crossExchangeArbitrage: {
				id: 'crossExchangeArbitrage',
				to: '/education/cross-exchange',
				text: '跨所套利策略',
				icon: 'HeroArrowsRightLeft',
				subPages: {
					signals: {
						id: 'crossExchangeSignals',
						to: '/education/cross-exchange/signals',
						text: '交易信号',
						icon: 'HeroBell',
					},
					orders: {
						id: 'crossExchangeOrders',
						to: '/education/cross-exchange/orders',
						text: '委托订单',
						icon: 'HeroClipboardDocumentList',
					},
					trades: {
						id: 'crossExchangeTrades',
						to: '/education/cross-exchange/trades',
						text: '成交订单',
						icon: 'HeroCheckCircle',
					},
					positions: {
						id: 'crossExchangePositions',
						to: '/education/cross-exchange/positions',
						text: '策略持仓',
						icon: 'HeroChartBar',
					},
				},
			},
			triangularArbitrage: {
				id: 'triangularArbitrage',
				to: '/education/triangular',
				text: '三角套利',
				icon: 'HeroTriangle',
				subPages: {
					signals: {
						id: 'triangularSignals',
						to: '/education/triangular/signals',
						text: '交易信号',
						icon: 'HeroBell',
					},
					orders: {
						id: 'triangularOrders',
						to: '/education/triangular/orders',
						text: '委托订单',
						icon: 'HeroClipboardDocumentList',
					},
					trades: {
						id: 'triangularTrades',
						to: '/education/triangular/trades',
						text: '成交订单',
						icon: 'HeroCheckCircle',
					},
					positions: {
						id: 'triangularPositions',
						to: '/education/triangular/positions',
						text: '策略持仓',
						icon: 'HeroChartBar',
					},
				},
			},
		},
	},
	reservationAppPages: {
		id: 'reservationApp',
		to: '/reservation',
		text: 'Reservation',
		icon: 'HeroCalendarDays',
		subPages: {},
	},
	mailAppPages: {
		id: 'mailApp',
		to: '/mail',
		text: 'Mail',
		icon: 'HeroEnvelope',
		subPages: {
			inboxPages: {
				id: 'inboxPages',
				to: '/mail/inbox',
				text: 'Inbox',
				icon: 'HeroEnvelope',
			},
			draftPages: {
				id: 'draftPages',
				to: '/mail/draft',
				text: 'Draft',
				icon: 'HeroDocument',
			},
			sendPages: {
				id: 'sendPages',
				to: '/mail/send',
				text: 'Send',
				icon: 'HeroPaperAirplane',
			},
			junkPages: {
				id: 'junkPages',
				to: '/mail/junk',
				text: 'Junk',
				icon: 'HeroArchiveBoxXMark',
			},
			trashPages: {
				id: 'trashPages',
				to: '/mail/trash',
				text: 'Trash',
				icon: 'HeroTrash',
			},
			archivePages: {
				id: 'archivePages',
				to: '/mail/archive',
				text: 'Archive',
				icon: 'HeroArchiveBox',
			},
			newMailPages: {
				id: 'newMailPages',
				to: '/mail/new',
				text: 'Inbox',
				icon: 'HeroEnvelope',
			},
		},
	},
	chatAppPages: {
		id: 'chatApp',
		to: '/chat',
		text: 'Chat',
		icon: 'HeroChatBubbleLeftRight',
	},
};

export const componentsPages = {
	uiPages: {
		id: 'uiPages',
		to: '/ui',
		text: 'UI',
		icon: 'HeroPuzzlePiece',
		subPages: {
			alertPage: {
				id: 'alertPage',
				to: '/ui/alert',
				text: 'Alert',
				icon: 'HeroBell',
			},
			badgePage: {
				id: 'badgePage',
				to: '/ui/badge',
				text: 'Badge',
				icon: 'HeroSparkles',
			},
			buttonPage: {
				id: 'buttonPage',
				to: '/ui/button',
				text: 'Button',
				icon: 'HeroRectangleStack',
			},
			buttonGroupPage: {
				id: 'buttonGroupPage',
				to: '/ui/button-group',
				text: 'Button Group',
				icon: 'HeroRectangleStack',
			},
			cardPage: {
				id: 'cardPage',
				to: '/ui/card',
				text: 'Card',
				icon: 'HeroSquare2Stack',
			},
			collapsePage: {
				id: 'collapsePage',
				to: '/ui/collapse',
				text: 'Collapse',
				icon: 'HeroBarsArrowDown',
			},
			dropdownPage: {
				id: 'dropdownPage',
				to: '/ui/dropdown',
				text: 'Dropdown',
				icon: 'HeroQueueList',
			},
			modalPage: {
				id: 'modalPage',
				to: '/ui/modal',
				text: 'Modal',
				icon: 'HeroChatBubbleBottomCenter',
			},
			offcanvasPage: {
				id: 'offcanvasPage',
				to: '/ui/offcanvas',
				text: 'Offcanvas',
				icon: 'HeroBars3BottomRight',
			},
			progressPage: {
				id: 'progressPage',
				to: '/ui/progress',
				text: 'Progress',
				icon: 'HeroChartBar',
			},
			tablePage: {
				id: 'tablePage',
				to: '/ui/table',
				text: 'Table',
				icon: 'HeroTableCells',
			},
			tooltipPage: {
				id: 'tooltipPage',
				to: '/ui/tooltip',
				text: 'Tooltip',
				icon: 'HeroChatBubbleLeftEllipsis',
			},
		},
	},
	formPages: {
		id: 'formPages',
		to: '/form',
		text: 'Form',
		icon: 'HeroPencilSquare',
		subPages: {
			fieldWrapPage: {
				id: 'fieldWrapPage',
				to: '/form/field-wrap',
				text: 'Field Wrap',
				icon: 'HeroInbox',
			},
			checkboxPage: {
				id: 'checkboxPage',
				to: '/form/checkbox',
				text: 'Checkbox',
				icon: 'HeroStop',
			},
			checkboxGroupPage: {
				id: 'checkboxGroupPage',
				to: '/form/checkbox-group',
				text: 'Checkbox Group',
				icon: 'HeroListBullet',
			},
			inputPage: {
				id: 'inputPage',
				to: '/form/input',
				text: 'Input',
				icon: 'HeroRectangleStack',
			},
			labelPage: {
				id: 'labelPage',
				to: '/form/label',
				text: 'Label',
				icon: 'HeroPencil',
			},
			radioPage: {
				id: 'radioPage',
				to: '/form/radio',
				text: 'Radio',
				icon: 'HeroStopCircle',
			},
			richTextPage: {
				id: 'richTextPage',
				to: '/form/rich-text',
				text: 'Rich Text',
				icon: 'HeroBars3CenterLeft',
			},
			selectPage: {
				id: 'selectPage',
				to: '/form/select',
				text: 'Select',
				icon: 'HeroQueueList',
			},
			selectReactPage: {
				id: 'selectReactPage',
				to: '/form/select-react',
				text: 'Select React',
				icon: 'HeroQueueList',
			},
			textareaPage: {
				id: 'textareaPage',
				to: '/form/textarea',
				text: 'Textarea',
				icon: 'HeroBars3BottomLeft',
			},
			validationPage: {
				id: 'validationPage',
				to: '/form/validation',
				text: 'Validation',
				icon: 'HeroShieldCheck',
			},
		},
	},
	integratedPages: {
		id: 'integratedPages',
		to: '/integrated',
		text: 'Integrated',
		icon: 'HeroBuildingLibrary',
		subPages: {
			reactDateRangePage: {
				id: 'reactDateRangePage',
				to: '/integrated/react-date-range',
				text: 'React Date Range',
				icon: 'HeroCalendarDays',
			},
			fullCalendarPage: {
				id: 'fullCalendarPage',
				to: '/integrated/full-calendar',
				text: 'Full Calendar',
				icon: 'HeroCalendar',
			},
			apexChartsPage: {
				id: 'apexChartsPage',
				to: '/integrated/apex-charts',
				text: 'ApexCharts',
				icon: 'HeroChartBar',
			},
			reactSimpleMapsPage: {
				id: 'reactSimpleMapsPage',
				to: '/integrated/react-simple-maps',
				text: 'React Simple Maps',
				icon: 'HeroMap',
			},
			waveSurferPage: {
				id: 'waveSurferPage',
				to: '/integrated/wave-surfer',
				text: 'WaveSurfer',
				icon: 'HeroMusicalNote',
			},
			richTextPage: {
				id: 'richTextPage',
				to: '/integrated/slate-react',
				text: 'Rich Text',
				icon: 'HeroBars3BottomLeft',
			},
			reactSelectPage: {
				id: 'reactSelectPage',
				to: '/integrated/react-select',
				text: 'React Select',
				icon: 'HeroQueueList',
			},
		},
	},
	iconsPage: {
		id: 'iconsPage',
		to: '/icons',
		text: 'Icons',
		icon: 'HeroBuildingLibrary',
		subPages: {
			heroiconsPage: {
				id: 'heroiconsPage',
				to: '/icons/heroicons',
				text: 'Heroicons',
				icon: 'HeroShieldCheck',
			},
			duotoneIconsPage: {
				id: 'duotoneIconsPage',
				to: '/icons/duotone-icons',
				text: 'Duotone Icons',
				icon: 'DuoPicker',
			},
		},
	},
};

export const authPages = {
	loginPage: {
		id: 'loginPage',
		to: '/login',
		text: 'Login',
		icon: 'HeroArrowRightOnRectangle',
	},
	profilePage: {
		id: 'profilePage',
		to: '/profile',
		text: 'Profile',
		icon: 'HeroUser',
	},
};

const pagesConfig = {
	...examplePages,
	...authPages,
};

export default pagesConfig;
