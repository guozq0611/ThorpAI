import React from 'react';
import Aside, { AsideBody } from '@/components/layouts/Aside/Aside';
import AsideHeadPart from '@/templates/layouts/Asides/_parts/AsideHead.part';
import Nav, { NavItem, NavSeparator } from '@/components/layouts/Navigation/Nav';
import { appPages } from '@/config/pages.config';
import Badge from '@/components/ui/Badge';
import AsideFooterPart from '@/templates/layouts/Asides/_parts/AsideFooter.part';

const MailAsideTemplate = () => {
	return (
		<Aside>
			<AsideHeadPart />
			<AsideBody>
				<Nav>
					<NavItem
						text='Inbox'
						icon='HeroInbox'
						to={appPages.mailAppPages.subPages.inboxPages.to}>
						<Badge
							variant='outline'
							color='emerald'
							className='border-transparent leading-none'>
							3
						</Badge>
					</NavItem>
					<NavItem {...appPages.mailAppPages.subPages.draftPages} />
					<NavItem {...appPages.mailAppPages.subPages.sendPages} />
					<NavItem {...appPages.mailAppPages.subPages.junkPages} />
					<NavItem {...appPages.mailAppPages.subPages.trashPages} />
					<NavItem {...appPages.mailAppPages.subPages.archivePages} />
					<NavSeparator />
					<NavItem
						{...appPages.salesAppPages.subPages.salesDashboardPage}
						text='Back to Home'
						icon='HeroArrowLeft'
					/>
				</Nav>
			</AsideBody>
			<AsideFooterPart />
		</Aside>
	);
};

export default MailAsideTemplate;
