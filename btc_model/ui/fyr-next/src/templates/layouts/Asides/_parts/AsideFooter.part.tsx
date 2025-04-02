import React from 'react';
import { AsideFooter } from '@/components/layouts/Aside/Aside';
import Nav, {
	NavButton,
	NavCollapse,
	NavItem,
	NavSeparator,
	NavTitle,
} from '@/components/layouts/Navigation/Nav';
import UserTemplate from '@/templates/layouts/User/User.template';
import DarkModeSwitcherPart from '@/templates/layouts/Asides/_parts/DarkModeSwitcher.part';
import Badge from '@/components/ui/Badge';

const AsideFooterPart = () => {
	return (
		<AsideFooter>
			<Nav>
				<NavSeparator />
				<NavCollapse text='Nav Collapse' to='/' icon='HeroQueueList'>
					<NavItem text='Nav item' icon='HeroPencil' />
					<NavItem text='With badge'>
						<Badge variant='solid' className='leading-none'>
							3
						</Badge>
					</NavItem>
					<NavItem text='With button'>
						<NavButton icon='HeroRocketLaunch' title='New' />
					</NavItem>
					<NavItem text='With badge & button'>
						<Badge variant='solid' className='leading-none'>
							3
						</Badge>
						<NavButton icon='HeroRocketLaunch' title='New' />
					</NavItem>
					<NavTitle>Navigation Title</NavTitle>
					<NavCollapse text='Nav Level 2' to='/' icon='HeroQueueList'>
						<NavItem text='Nav Item' />
						<NavCollapse text='Nav Level 3' to='/' icon='HeroQueueList'>
							<NavItem text='Nav Item' />
						</NavCollapse>
						<NavItem text='Nav Item' />
					</NavCollapse>
				</NavCollapse>
			</Nav>

			<UserTemplate />
			<DarkModeSwitcherPart />
		</AsideFooter>
	);
};

export default AsideFooterPart;
